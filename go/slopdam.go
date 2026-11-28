// SPDX-License-Identifier: MIT

// Package slopdam strips the traces AI coding tools leave in log messages: em dashes and
// the Korean ㅡ, emoji, separator lines, markdown bold, curly quotes and invisible characters.
//
// It is the Go port of slopdam (https://github.com/slopdam/slopdam). Rules, character sets
// and their order come from the repository's language-neutral spec; only the four
// context-dependent actions are written here, following spec/README.md step by step.
//
//	slopdam.Clean("✅ **Saved** — 3 rows 🎉")          // "Saved: 3 rows"
//
//	dev, _ := slopdam.New(slopdam.Options{Profile: "dev"})
//	dev.Clean("✅ Upload done — 3 files")              // "[OK] Upload done - 3 files"
package slopdam

//go:generate go run ./internal/specgen

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/dlclark/regexp2"
)

// Options select how text is cleaned. The zero value is the default: reader, basic, colon.
type Options struct {
	// Profile is "reader" (default): plain text for people, or "dev": grep-friendly text.
	Profile string
	// Level is "basic" (default), "strong" or "strict".
	Level string
	// Disable lists rule IDs or groups to turn off, such as "emoji" or "dash.run".
	Disable []string
	// DashInline is what an inline dash becomes in reader: "colon" (default), "comma",
	// "hyphen" or "space".
	DashInline string
}

// Finding is one trace clean would change. Start and End are byte offsets into the input.
type Finding struct {
	RuleID      string
	Description string
	Start, End  int
	Text        string
	// Fix is the replacement, or nil when the rule only reports.
	Fix *string
}

// Log levels on Python's logging scale, used to drop a dev status tag the level already says.
const (
	LevelNone     = -1
	LevelDebug    = 10
	LevelInfo     = 20
	LevelWarning  = 30
	LevelError    = 40
	LevelCritical = 50
)

type actionSpec struct {
	Kind  string `json:"kind"`
	Value string `json:"value"`
	Name  string `json:"name"`
}

type ruleSpec struct {
	ID          string                `json:"id"`
	Level       string                `json:"level"`
	Description string                `json:"description"`
	Pattern     string                `json:"pattern"`
	Flags       []string              `json:"flags"`
	Actions     map[string]actionSpec `json:"actions"`
}

type rulesSpec struct {
	SpecVersion       int               `json:"spec_version"`
	Profiles          []string          `json:"profiles"`
	Levels            []string          `json:"levels"`
	DashInline        map[string]string `json:"dash_inline"`
	DefaultDashInline string            `json:"default_dash_inline"`
	ProtectedSpans    string            `json:"protected_spans"`
	Charsets          struct {
		Status         map[string]string `json:"status"`
		HangulChoseong string            `json:"hangul_choseong"`
		HanKana        string            `json:"han_kana"`
	} `json:"charsets"`
	DashWordBefore string `json:"dash_word_before"`
	DashWordAfter  string `json:"dash_word_after"`
	Tidy           struct {
		Scope      string `json:"scope"`
		MultiSpace string `json:"multi_space"`
		QuoteSpace string `json:"quote_space"`
		MaxPasses  int    `json:"max_passes"`
	} `json:"tidy"`
	StatusRedundantAt map[string]string `json:"status_redundant_at"`
	Rules             []ruleSpec        `json:"rules"`
}

var (
	spec       rulesSpec
	protect    *regexp2.Regexp
	multiSpace *regexp2.Regexp
	quoteSpace *regexp2.Regexp
	choseong   *regexp2.Regexp
	hanKana    *regexp2.Regexp
	statusOf   = map[rune]string{}
	compiled   = map[int]*regexp2.Regexp{}
)

// SpecVersion is the version of slopdam's spec this package implements.
var SpecVersion int

func init() {
	if err := json.Unmarshal([]byte(rulesJSON), &spec); err != nil {
		panic("slopdam: bad embedded spec: " + err.Error())
	}
	SpecVersion = spec.SpecVersion
	must := func(p string, flags []string) *regexp2.Regexp {
		re, err := compile(p, flags)
		if err != nil {
			panic(err)
		}
		return re
	}
	protect = must(spec.ProtectedSpans, nil)
	multiSpace = must(spec.Tidy.MultiSpace, nil)
	quoteSpace = must(spec.Tidy.QuoteSpace, nil)
	choseong = regexp2.MustCompile("^["+spec.Charsets.HangulChoseong+"]$", regexp2.None)
	hanKana = regexp2.MustCompile("["+spec.Charsets.HanKana+"]", regexp2.None)
	for tag, chars := range spec.Charsets.Status {
		for _, c := range chars {
			statusOf[c] = tag
		}
	}
	for i, r := range spec.Rules {
		compiled[i] = must(r.Pattern, r.Flags)
	}
	defaultSanitizer = MustNew(Options{})
}

const pua = 0xF0000

func isPUA(r rune) bool { return r >= 0xF0000 && r <= 0xFFFFD }

type cleanCtx struct {
	profile    string
	dashInline string
	levelno    int
}

type action func(m *regexp2.Match, s []rune, ctx *cleanCtx) string

func group(m *regexp2.Match, n int) string {
	g := m.GroupByNumber(n)
	if g == nil || len(g.Captures) == 0 {
		return ""
	}
	return g.String()
}

func levelNumber(name string) int {
	switch strings.ToUpper(name) {
	case "CRITICAL", "FATAL":
		return LevelCritical
	case "ERROR":
		return LevelError
	case "WARNING", "WARN":
		return LevelWarning
	case "INFO":
		return LevelInfo
	case "DEBUG":
		return LevelDebug
	}
	return LevelNone
}

func wordish(r rune, extra string) bool {
	return isAlnum(r) || strings.ContainsRune(extra, r) || isPUA(r)
}

var functions = map[string]action{
	// Chinese and Japanese write this punctuation full width, so a line with kana or CJK
	// ideographs keeps it; elsewhere it becomes ASCII.
	"fullwidth": func(m *regexp2.Match, text []rune, _ *cleanCtx) string {
		start, end := m.Index, m.Index
		for start > 0 && text[start-1] != '\n' {
			start--
		}
		for end < len(text) && text[end] != '\n' {
			end++
		}
		if ok, _ := hanKana.MatchString(string(text[start:end])); ok {
			return m.String()
		}
		return strings.Map(func(r rune) rune {
			if r >= 0xFF01 && r <= 0xFF5E {
				return r - 0xFEE0
			}
			return r
		}, m.String())
	},
	"unwrap": func(m *regexp2.Match, _ []rune, _ *cleanCtx) string { return group(m, 1) },
	// Inside a double-quoted string a plain quote would end it, so it is escaped.
	"quote_double": func(m *regexp2.Match, text []rune, _ *cleanCtx) string {
		start := m.Index
		for start > 0 && text[start-1] != '\n' {
			start--
		}
		n := 0
		for j := start; j < m.Index; j++ {
			if text[j] == '"' && (j == start || text[j-1] != '\\') {
				n++
			}
		}
		if n%2 == 1 {
			return `\"`
		}
		return `"`
	},
	"status_tag": func(m *regexp2.Match, _ []rune, ctx *cleanCtx) string {
		r, _ := utf8.DecodeRuneInString(group(m, 1))
		tag := statusOf[r]
		if at, ok := spec.StatusRedundantAt[tag]; ok && ctx.levelno != LevelNone && ctx.levelno >= levelNumber(at) {
			return ""
		}
		return tag + " "
	},
	"dash_run": func(m *regexp2.Match, s []rune, ctx *cleanCtx) string {
		start, end := m.Index, m.Index+m.Length
		lead, run, trail := group(m, 1), []rune(group(m, 2)), group(m, 3)
		leadLen := utf8.RuneCountInString(lead)
		if run[0] == 'ᅳ' && start+leadLen > 0 {
			if ok, _ := choseong.MatchString(string(s[start+leadLen-1])); ok {
				return m.String() // part of a composed old-style syllable
			}
		}
		prev, next := '\n', '\n'
		if start > 0 {
			prev = s[start-1]
		}
		if end < len(s) {
			next = s[end]
		}
		inner := wordish(prev, spec.DashWordBefore) && wordish(next, spec.DashWordAfter)
		if len(run) >= 2 { // separator or emoticon: ㅡㅡ, ──
			if inner {
				return " "
			}
			return ""
		}
		if isDigit(prev) && isDigit(next) {
			if ctx.profile == "reader" {
				return "~"
			}
			return "-"
		}
		lineStart := 0
		for i := start - 1; i >= 0; i-- {
			if s[i] == '\n' {
				lineStart = i + 1
				break
			}
		}
		if len(pyStrip(s[lineStart:start])) == 0 && trail != "" {
			return lead + "- " // list marker at line start
		}
		if inner {
			if ctx.profile == "reader" {
				return ctx.dashInline
			}
			return " - "
		}
		return ""
	},
}

// expand is Python's Match.expand for the replacement strings in the spec (\1, \g<1>).
func expand(template string, m *regexp2.Match) string {
	var out strings.Builder
	for i := 0; i < len(template); i++ {
		c := template[i]
		if c != '\\' || i+1 >= len(template) {
			out.WriteByte(c)
			continue
		}
		n := template[i+1]
		switch {
		case n >= '0' && n <= '9':
			j := i + 1
			for j < len(template) && template[j] >= '0' && template[j] <= '9' {
				j++
			}
			idx, _ := strconv.Atoi(template[i+1 : j])
			out.WriteString(group(m, idx))
			i = j - 1
		case n == 'g' && i+2 < len(template) && template[i+2] == '<':
			end := strings.IndexByte(template[i+3:], '>')
			name := template[i+3 : i+3+end]
			if idx, err := strconv.Atoi(name); err == nil {
				out.WriteString(group(m, idx))
			} else if g := m.GroupByName(name); g != nil && len(g.Captures) > 0 {
				out.WriteString(g.String())
			}
			i += 3 + end
		case n == 'n':
			out.WriteByte('\n')
			i++
		case n == 't':
			out.WriteByte('\t')
			i++
		case n == '\\':
			out.WriteByte('\\')
			i++
		default:
			out.WriteByte(c)
		}
	}
	return out.String()
}

// sub is Python's re.sub with a function: every non-overlapping match, left to right.
func sub(re *regexp2.Regexp, s []rune, fn func(m *regexp2.Match) string) []rune {
	m, _ := re.FindRunesMatch(s)
	if m == nil {
		return s
	}
	out := make([]rune, 0, len(s))
	last := 0
	for m != nil {
		out = append(out, s[last:m.Index]...)
		out = append(out, []rune(fn(m))...)
		last = m.Index + m.Length
		m, _ = re.FindNextMatch(m)
	}
	return append(out, s[last:]...)
}

type rule struct {
	id          string
	description string
	re          *regexp2.Regexp
	action      action // nil: report only
}

// Sanitizer cleans text with one profile and level. It is safe for concurrent use.
type Sanitizer struct {
	profile    string
	dashInline string
	rules      []rule
}

func contains(list []string, v string) bool {
	for _, x := range list {
		if x == v {
			return true
		}
	}
	return false
}

func index(list []string, v string) int {
	for i, x := range list {
		if x == v {
			return i
		}
	}
	return -1
}

// New returns a Sanitizer for the options, or an error for an unknown profile, level or
// dash style.
func New(o Options) (*Sanitizer, error) {
	if o.Profile == "" {
		o.Profile = "reader"
	}
	if o.Level == "" {
		o.Level = "basic"
	}
	if o.DashInline == "" {
		o.DashInline = spec.DefaultDashInline
	}
	if !contains(spec.Profiles, o.Profile) {
		return nil, fmt.Errorf("slopdam: unknown profile %q, expected one of %v", o.Profile, spec.Profiles)
	}
	if !contains(spec.Levels, o.Level) {
		return nil, fmt.Errorf("slopdam: unknown level %q, expected one of %v", o.Level, spec.Levels)
	}
	inline, ok := spec.DashInline[o.DashInline]
	if !ok {
		return nil, fmt.Errorf("slopdam: unknown dash inline style %q", o.DashInline)
	}
	s := &Sanitizer{profile: o.Profile, dashInline: inline}
	for i, r := range spec.Rules {
		if index(spec.Levels, r.Level) > index(spec.Levels, o.Level) {
			continue
		}
		off := false
		for _, d := range o.Disable {
			if r.ID == d || strings.HasPrefix(r.ID, d+".") {
				off = true
			}
		}
		a, ok := r.Actions[o.Profile]
		if off || !ok {
			continue
		}
		var act action
		switch a.Kind {
		case "replace":
			value := a.Value
			act = func(m *regexp2.Match, _ []rune, _ *cleanCtx) string { return expand(value, m) }
		case "function":
			act = functions[a.Name]
			if act == nil {
				return nil, fmt.Errorf("slopdam: spec function %s is not implemented", a.Name)
			}
		}
		s.rules = append(s.rules, rule{id: r.ID, description: r.Description, re: compiled[i], action: act})
	}
	return s, nil
}

// MustNew is New that panics on invalid options.
func MustNew(o Options) *Sanitizer {
	s, err := New(o)
	if err != nil {
		panic(err)
	}
	return s
}

// defaultSanitizer is set at the end of init, once the spec is loaded.
var defaultSanitizer *Sanitizer

// Clean removes AI traces with the default options (reader, basic).
func Clean(text string) string { return defaultSanitizer.Clean(text) }

func (s *Sanitizer) apply(text []rune, ctx *cleanCtx) []rune {
	for _, r := range s.rules {
		if r.action == nil {
			continue
		}
		act := r.action
		text = sub(r.re, text, func(m *regexp2.Match) string { return act(m, text, ctx) })
	}
	return text
}

// Clean removes AI traces from text.
func (s *Sanitizer) Clean(text string) string { return s.CleanLevel(text, LevelNone) }

// CleanLevel is Clean for a log record at the given level (LevelError, LevelWarning, ...), so
// that dev drops a [FAIL] or [WARN] tag the level already says.
func (s *Sanitizer) CleanLevel(text string, level int) string {
	ctx := &cleanCtx{profile: s.profile, dashInline: s.dashInline, levelno: level}
	cur := joinLines(splitlines([]rune(text)))
	for pass := 0; pass < spec.Tidy.MaxPasses; pass++ {
		next := s.cleanOnce(cur, ctx)
		if string(next) == string(cur) {
			break
		}
		cur = next
	}
	return string(cur)
}

func joinLines(lines [][]rune) []rune {
	var out []rune
	for i, l := range lines {
		if i > 0 {
			out = append(out, '\n')
		}
		out = append(out, l...)
	}
	return out
}

func (s *Sanitizer) cleanOnce(text []rune, ctx *cleanCtx) []rune {
	var saved [][]rune
	masked := sub(protect, text, func(m *regexp2.Match) string {
		kept := []rune(m.String())
		// reader drops the backticks, but only when the code itself is clean.
		if g := m.GroupByName("code"); g != nil && len(g.Captures) > 0 && s.profile == "reader" {
			code := []rune(g.String())
			if string(s.apply(code, ctx)) == string(code) {
				kept = code
			}
		}
		saved = append(saved, kept)
		return string(rune(pua + len(saved) - 1))
	})
	out := s.apply(masked, ctx)
	// No rule adds or removes a line break, so lines compare one to one. Only lines a rule
	// changed are tidied, while protected spans are still masked.
	before := strings.Split(string(masked), "\n")
	after := strings.Split(string(out), "\n")
	for i, line := range after {
		if i < len(before) && line == before[i] {
			continue
		}
		r := sub(multiSpace, []rune(line), func(*regexp2.Match) string { return " " })
		after[i] = string(sub(quoteSpace, r, func(*regexp2.Match) string { return "" }))
	}
	out = []rune(strings.Join(after, "\n"))
	restored := make([]rune, 0, len(out))
	for _, r := range out {
		if isPUA(r) && int(r-pua) < len(saved) {
			restored = append(restored, saved[r-pua]...)
		} else {
			restored = append(restored, r)
		}
	}
	var lines [][]rune
	for _, line := range splitlines(restored) {
		if len(lines) > 0 {
			line = pyRstrip(line)
		} else {
			line = pyStrip(line)
		}
		if len(line) > 0 {
			lines = append(lines, line)
		}
	}
	return joinLines(lines)
}

// Findings reports what Clean would change, in one pass and without tidying, with byte
// offsets into text.
func (s *Sanitizer) Findings(text string) []Finding {
	ctx := &cleanCtx{profile: s.profile, dashInline: s.dashInline, levelno: LevelNone}
	orig := []rune(text)
	var work []rune
	var spans [][2]int // per rune of work: its span in orig (runes)
	last := 0
	m, _ := protect.FindRunesMatch(orig)
	for m != nil {
		for i := last; i < m.Index; i++ {
			work = append(work, orig[i])
			spans = append(spans, [2]int{i, i + 1})
		}
		work = append(work, pua)
		spans = append(spans, [2]int{m.Index, m.Index + m.Length})
		last = m.Index + m.Length
		m, _ = protect.FindNextMatch(m)
	}
	for i := last; i < len(orig); i++ {
		work = append(work, orig[i])
		spans = append(spans, [2]int{i, i + 1})
	}

	type hit struct {
		rule       rule
		start, end int
		fix        *string
	}
	var found []hit
	for _, r := range s.rules {
		var pieces []rune
		var newSpans [][2]int
		pos, start, end := 0, 0, 0
		changed := false
		m, _ := r.re.FindRunesMatch(work)
		for m != nil {
			var fix *string
			if r.action != nil {
				f := r.action(m, work, ctx)
				fix = &f
			}
			text := m.String()
			if m.Length > 0 {
				start, end = spans[m.Index][0], spans[m.Index+m.Length-1][1]
				if len(pyStrip([]rune(text))) > 0 && (fix == nil || *fix != text) {
					found = append(found, hit{r, start, end, fix})
				}
			}
			if fix != nil && *fix != text {
				changed = true
				pieces = append(pieces, work[pos:m.Index]...)
				newSpans = append(newSpans, spans[pos:m.Index]...)
				fr := []rune(*fix)
				pieces = append(pieces, fr...)
				for range fr {
					newSpans = append(newSpans, [2]int{start, end})
				}
				pos = m.Index + m.Length
			}
			m, _ = r.re.FindNextMatch(m)
		}
		if changed {
			pieces = append(pieces, work[pos:]...)
			newSpans = append(newSpans, spans[pos:]...)
			work, spans = pieces, newSpans
		}
	}

	// sort by (start, -end), then drop hits nested inside an earlier one
	for i := 1; i < len(found); i++ {
		for j := i; j > 0 && (found[j].start < found[j-1].start || (found[j].start == found[j-1].start && found[j].end > found[j-1].end)); j-- {
			found[j], found[j-1] = found[j-1], found[j]
		}
	}
	byteAt := make([]int, len(orig)+1)
	for i, r := range orig {
		byteAt[i+1] = byteAt[i] + utf8.RuneLen(r)
	}
	var kept []hit
	var out []Finding
	for _, f := range found {
		nested := false
		for _, k := range kept {
			if k.start <= f.start && f.end <= k.end {
				nested = true
				break
			}
		}
		if nested {
			continue
		}
		kept = append(kept, f)
		out = append(out, Finding{
			RuleID: f.rule.id, Description: f.rule.description,
			Start: byteAt[f.start], End: byteAt[f.end],
			Text: string(pyStrip(orig[f.start:f.end])), Fix: f.fix,
		})
	}
	return out
}
