// SPDX-License-Identifier: MIT

// Package vet is a go/analysis analyzer that reports AI traces (em dashes, emoji, separators,
// markdown) in the string arguments of log calls and suggests fixes.
//
//	go install github.com/slopdam/slopdam/go/vet/cmd/slopdamvet@latest
//	slopdamvet ./...            # report
//	slopdamvet -fix ./...       # apply the suggested fixes
//	go vet -vettool=$(which slopdamvet) ./...
//
// Like `slopdam fix` for Python, a fix edits only the text of the literal: quotes, escape
// sequences and format verbs such as %v or %d stay as they are, and no space is added at
// either end.
package vet

import (
	"fmt"
	"go/ast"
	"go/token"
	"regexp"
	"strings"
	"unicode/utf8"

	"golang.org/x/tools/go/analysis"
	"golang.org/x/tools/go/analysis/passes/inspect"
	"golang.org/x/tools/go/ast/inspector"

	"github.com/slopdam/slopdam/go"
)

var (
	profile    string
	level      string
	disable    string
	dashInline string
	receivers  string
)

// Analyzer reports AI traces in log call arguments.
var Analyzer = &analysis.Analyzer{
	Name:     "slopdam",
	Doc:      "report AI-generated traces (em dashes, emoji, separators, markdown) in log messages",
	URL:      "https://github.com/slopdam/slopdam/blob/main/go/README.md",
	Requires: []*analysis.Analyzer{inspect.Analyzer},
	Run:      run,
}

func init() {
	Analyzer.Flags.StringVar(&profile, "profile", "reader", "reader (plain text for people) or dev (grep-friendly)")
	Analyzer.Flags.StringVar(&level, "level", "basic", "basic, strong or strict")
	Analyzer.Flags.StringVar(&disable, "disable", "", "comma-separated rule IDs or groups to turn off, such as emoji,dash.run")
	Analyzer.Flags.StringVar(&dashInline, "dash-inline", "colon", "what an inline dash becomes in reader: colon, comma, hyphen or space")
	Analyzer.Flags.StringVar(&receivers, "receivers", `(?i)log|^fmt$`, "regular expression for the receiver or package of a log call")
}

// Method names of log calls: log, log/slog, fmt printing and the usual logger methods.
var methods = map[string]bool{}

func init() {
	for _, m := range strings.Fields(`Print Printf Println Fatal Fatalf Fatalln Panic Panicf Panicln
		Fprint Fprintf Fprintln Debug Debugf Debugw Info Infof Infow Warn Warnf Warnw Warning Warningf
		Error Errorf Errorw DebugContext InfoContext WarnContext ErrorContext Log Logf LogAttrs Trace Tracef`) {
		methods[m] = true
	}
}

// Format verbs and %% are masked so no rule edits them; fmt's verbs plus Python's printf ones.
var verb = regexp.MustCompile(`%[-+# 0]*(?:\[\d+\])?(?:\*|\d+)?(?:\.(?:\*|\d+)?)?[vTtbcdoOqxXUeEfFgGsp%]`)

// Each masked piece becomes one character from the private-use plane, which the rules treat
// as part of a word and never change.
const maskBase = 0xF8000

func run(pass *analysis.Pass) (any, error) {
	var off []string
	if disable != "" {
		off = strings.Split(disable, ",")
	}
	s, err := slopdam.New(slopdam.Options{Profile: profile, Level: level, Disable: off, DashInline: dashInline})
	if err != nil {
		return nil, err
	}
	recv, err := regexp.Compile(receivers)
	if err != nil {
		return nil, fmt.Errorf("slopdam: -receivers: %w", err)
	}
	ins := pass.ResultOf[inspect.Analyzer].(*inspector.Inspector)
	ins.Preorder([]ast.Node{(*ast.CallExpr)(nil)}, func(n ast.Node) {
		call := n.(*ast.CallExpr)
		sel, ok := call.Fun.(*ast.SelectorExpr)
		if !ok || !methods[sel.Sel.Name] || !recv.MatchString(exprText(sel.X)) {
			return
		}
		for _, arg := range call.Args {
			parts := operands(arg, nil)
			for i, p := range parts {
				if lit, ok := p.(*ast.BasicLit); ok && lit.Kind == token.STRING {
					check(pass, s, lit, i > 0, i < len(parts)-1)
				}
			}
		}
	})
	return nil, nil
}

// exprText is the receiver as written: log, slog, h.logger, s.log.
func exprText(e ast.Expr) string {
	switch x := e.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.SelectorExpr:
		return exprText(x.X) + "." + x.Sel.Name
	case *ast.CallExpr:
		return exprText(x.Fun) + "()"
	case *ast.StarExpr:
		return exprText(x.X)
	case *ast.ParenExpr:
		return exprText(x.X)
	}
	return ""
}

// operands flattens a + chain: "a" + b + "c" -> ["a", b, "c"].
func operands(e ast.Expr, out []ast.Expr) []ast.Expr {
	if b, ok := e.(*ast.BinaryExpr); ok && b.Op == token.ADD {
		return operands(b.Y, operands(b.X, out))
	}
	return append(out, e)
}

type masked struct {
	text   []rune
	pieces []string
	where  []int // rune index in text -> rune index in the body
}

func mask(body []rune, spans [][2]int) masked {
	var m masked
	last := 0
	for _, sp := range spans {
		for i := last; i < sp[0]; i++ {
			m.text = append(m.text, body[i])
			m.where = append(m.where, i)
		}
		m.text = append(m.text, rune(maskBase+len(m.pieces)))
		m.where = append(m.where, sp[0])
		m.pieces = append(m.pieces, string(body[sp[0]:sp[1]]))
		last = sp[1]
	}
	for i := last; i <= len(body); i++ {
		if i < len(body) {
			m.text = append(m.text, body[i])
		}
		m.where = append(m.where, i)
	}
	return m
}

func unmask(text []rune, pieces []string) (string, bool) {
	var out strings.Builder
	next := 0
	for _, r := range text {
		n := int(r) - maskBase
		if n >= 0 && n < len(pieces) {
			if n != next {
				return "", false // a rule moved or swallowed a piece
			}
			out.WriteString(pieces[n])
			next++
			continue
		}
		out.WriteRune(r)
	}
	return out.String(), next == len(pieces)
}

// rewrite applies each finding's fix at its span, as the Python fixer does; overlapping
// findings are skipped. It fails when a fix cannot be written inside the literal.
func rewrite(s *slopdam.Sanitizer, text, quote string) (string, bool) {
	var out strings.Builder
	last := 0
	for _, f := range s.Findings(text) {
		if f.Start < last || f.Fix == nil {
			continue
		}
		fix := *f.Fix
		if quote == "`" && strings.Contains(fix, "`") {
			return "", false // a raw string cannot hold a backquote
		}
		if quote == `"` {
			fix = strings.ReplaceAll(strings.ReplaceAll(fix, `\`, `\\`), `"`, `\"`)
		}
		out.WriteString(text[last:f.Start])
		out.WriteString(fix)
		last = f.End
	}
	out.WriteString(text[last:])
	return out.String(), true
}

// runeIndex maps a byte offset in s to a rune index.
func runeIndex(s string, b int) int { return utf8.RuneCountInString(s[:b]) }

func check(pass *analysis.Pass, s *slopdam.Sanitizer, lit *ast.BasicLit, joinedBefore, joinedAfter bool) {
	quote := lit.Value[:1]
	body := []rune(lit.Value[1 : len(lit.Value)-1])
	var spans [][2]int
	if joinedBefore {
		spans = append(spans, [2]int{0, 0})
	}
	bodyStr := string(body)
	for _, loc := range verb.FindAllStringIndex(bodyStr, -1) {
		if bodyStr[loc[0]:loc[1]] == "%%" {
			continue
		}
		spans = append(spans, [2]int{runeIndex(bodyStr, loc[0]), runeIndex(bodyStr, loc[1])})
	}
	if joinedAfter {
		spans = append(spans, [2]int{len(body), len(body)})
	}
	m := mask(body, spans)
	text := string(m.text)
	found := s.Findings(text)
	if len(found) == 0 {
		return
	}

	// Report what the first pass finds, overlapping findings skipped.
	var shown []slopdam.Finding
	last := 0
	for _, f := range found {
		if f.Start >= last {
			shown = append(shown, f)
			last = f.End
		}
	}
	// Apply the fixes and repeat until nothing changes: removing one trace can expose another
	// (the dash in "‒•" leaves a bullet at the start of the line), as in Clean.
	cur, possible := text, true
	for pass := 0; pass < 8; pass++ {
		next, ok := rewrite(s, cur, quote)
		if !ok {
			possible = false
			break
		}
		if next == cur {
			break
		}
		cur = next
	}
	newBody, ok := unmask([]rune(cur), m.pieces)
	if ok && possible {
		if strings.TrimLeft(bodyStr, " \t\n") == bodyStr {
			newBody = strings.TrimLeft(newBody, " \t")
		}
		if strings.TrimRight(bodyStr, " \t\n") == bodyStr {
			newBody = strings.TrimRight(newBody, " \t")
		}
	}
	var fixes []analysis.SuggestedFix
	if ok && possible && newBody != bodyStr {
		fixes = []analysis.SuggestedFix{{
			Message:   "Remove AI traces from the log message",
			TextEdits: []analysis.TextEdit{{Pos: lit.Pos(), End: lit.End(), NewText: []byte(quote + newBody + quote)}},
		}}
	}

	bodyBytes := func(runeIdx int) int { return len(string(body[:runeIdx])) }
	for i, f := range shown {
		from := m.where[runeIndex(text, f.Start)]
		to := m.where[runeIndex(text, f.End)]
		shownText := strings.TrimSpace(string(body[from:to])) // the source text, not the masked one
		msg := fmt.Sprintf("slopdam %s: %q", f.RuleID, shownText)
		if f.Fix != nil {
			msg = fmt.Sprintf("slopdam %s: %q should be %q", f.RuleID, shownText, *f.Fix)
		}
		d := analysis.Diagnostic{
			Pos:      lit.Pos() + 1 + token.Pos(bodyBytes(from)),
			End:      lit.Pos() + 1 + token.Pos(bodyBytes(to)),
			Category: f.RuleID,
			Message:  msg,
		}
		if i == 0 {
			d.SuggestedFixes = fixes // one edit per literal fixes every finding in it
		}
		pass.Report(d)
	}
}
