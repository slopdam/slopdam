// SPDX-License-Identifier: MIT

package slopdam

// Translate the Python re patterns in the spec into regexp2 patterns with Python's meaning.
// Go's own regexp (RE2) has no lookbehind or back references, which the spec uses, so the
// engine is github.com/dlclark/regexp2. The translation mirrors js/src/pyregex.ts:
//
//	\w \s \d \b   Unicode-aware, as in Python 3, written out as explicit classes
//	\A \Z         start and end of the whole string
//	\UXXXXXXXX    the character itself
//	.             any character except \n
//	^ $           Python's anchors; with the multiline flag only \n separates lines
//	(?P<name>     (?<name>

import (
	"fmt"
	"strconv"
	"strings"
	"unicode"

	"github.com/dlclark/regexp2"
)

const (
	pyWord  = `\p{L}\p{N}_`
	pySpace = `\t-\r\x1c-\x20\x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000`
)

var wordBoundary = `(?:(?<=[` + pyWord + `])(?![` + pyWord + `])|(?<![` + pyWord + `])(?=[` + pyWord + `]))`

// Characters JavaScript and .NET-style engines allow after a backslash with a special meaning.
const syntaxChars = `^$\.*+?()[]{}|/`

func translate(src string, multiline bool) (string, error) {
	var out strings.Builder
	rs := []rune(src)
	inClass := false
	fail := func(what string) (string, error) {
		return "", fmt.Errorf("slopdam: cannot translate %s in /%s/", what, src)
	}
	for i := 0; i < len(rs); {
		ch := rs[i]
		if ch == '\\' {
			if i+1 >= len(rs) {
				return fail("a trailing backslash")
			}
			n := rs[i+1]
			i += 2
			switch n {
			case 'w':
				if inClass {
					out.WriteString(pyWord)
				} else {
					out.WriteString("[" + pyWord + "]")
				}
				continue
			case 's':
				if inClass {
					out.WriteString(pySpace)
				} else {
					out.WriteString("[" + pySpace + "]")
				}
				continue
			case 'd':
				out.WriteString(`\p{Nd}`)
				continue
			case 'W', 'S', 'D', 'B', 'A', 'Z':
				if inClass {
					return fail(`\` + string(n) + " in a class")
				}
				switch n {
				case 'W':
					out.WriteString("[^" + pyWord + "]")
				case 'S':
					out.WriteString("[^" + pySpace + "]")
				case 'D':
					out.WriteString(`\P{Nd}`)
				case 'B':
					out.WriteString("(?!" + wordBoundary + ")")
				case 'A':
					out.WriteString(`(?<![\s\S])`)
				case 'Z':
					out.WriteString(`(?![\s\S])`)
				}
				continue
			case 'b':
				if inClass {
					out.WriteString(`\x08`)
				} else {
					out.WriteString(wordBoundary)
				}
				continue
			case 'U':
				if i+8 > len(rs) {
					return fail(`\U`)
				}
				cp, err := strconv.ParseUint(string(rs[i:i+8]), 16, 32)
				if err != nil {
					return fail(`\U` + string(rs[i:i+8]))
				}
				out.WriteRune(rune(cp))
				i += 8
				continue
			case 'u':
				out.WriteString(`\u` + string(rs[i:i+4]))
				i += 4
				continue
			case 'x':
				out.WriteString(`\x` + string(rs[i:i+2]))
				i += 2
				continue
			case 'n', 't', 'r', 'f', 'v', '0':
				out.WriteString(`\` + string(n))
				continue
			}
			switch {
			case n >= '1' && n <= '9':
				out.WriteString(`\` + string(n))
			case unicode.IsLetter(n) || unicode.IsDigit(n):
				return fail(`\` + string(n))
			case strings.ContainsRune(syntaxChars, n) || (inClass && n == '-'):
				out.WriteString(`\` + string(n))
			default:
				out.WriteRune(n)
			}
			continue
		}
		if inClass {
			if ch == ']' {
				inClass = false
			}
			out.WriteRune(ch)
			i++
			continue
		}
		switch {
		case ch == '[':
			inClass = true
			out.WriteRune(ch)
			i++
			if i < len(rs) && rs[i] == '^' {
				out.WriteRune('^')
				i++
			}
			if i < len(rs) && rs[i] == ']' {
				out.WriteString(`\]`)
				i++
			}
		case ch == '.':
			out.WriteString(`[^\n]`)
			i++
		case ch == '^':
			if multiline {
				out.WriteString(`(?<![^\n])`)
			} else {
				out.WriteString(`(?<![\s\S])`)
			}
			i++
		case ch == '$':
			if multiline {
				out.WriteString(`(?![^\n])`)
			} else {
				out.WriteString(`(?=\n?(?![\s\S]))`)
			}
			i++
		case strings.HasPrefix(string(rs[i:]), "(?P<"):
			out.WriteString("(?<")
			i += 4
		case strings.HasPrefix(string(rs[i:]), "(?P=") || strings.HasPrefix(string(rs[i:]), "(?#"):
			return fail("a named back reference or comment")
		default:
			out.WriteRune(ch)
			i++
		}
	}
	return out.String(), nil
}

func compile(pattern string, flags []string) (*regexp2.Regexp, error) {
	multiline := false
	for _, f := range flags {
		if f == "multiline" {
			multiline = true
		}
	}
	src, err := translate(pattern, multiline)
	if err != nil {
		return nil, err
	}
	return regexp2.Compile(src, regexp2.None)
}

// Python's character tests, measured on its Unicode database: str.isalnum() is letters and
// numbers (L*, N*); str.isdigit() is Nd plus these; whitespace is the pySpace set.
var digitExtra = &unicode.RangeTable{
	R16: []unicode.Range16{
		{0xB2, 0xB3, 1}, {0xB9, 0xB9, 1}, {0x1369, 0x1371, 1}, {0x19DA, 0x19DA, 1},
		{0x2070, 0x2070, 1}, {0x2074, 0x2079, 1}, {0x2080, 0x2089, 1}, {0x2460, 0x2468, 1},
		{0x2474, 0x247C, 1}, {0x2488, 0x2490, 1}, {0x24EA, 0x24EA, 1}, {0x24F5, 0x24FD, 1},
		{0x24FF, 0x24FF, 1}, {0x2776, 0x277E, 1}, {0x2780, 0x2788, 1}, {0x278A, 0x2792, 1},
	},
	R32: []unicode.Range32{
		{0x10A40, 0x10A43, 1}, {0x10E60, 0x10E68, 1}, {0x11052, 0x1105A, 1}, {0x1F100, 0x1F10A, 1},
	},
}

func isAlnum(r rune) bool { return unicode.IsLetter(r) || unicode.IsNumber(r) }
func isDigit(r rune) bool { return unicode.Is(unicode.Nd, r) || unicode.Is(digitExtra, r) }

func isSpace(r rune) bool {
	switch {
	case r >= '\t' && r <= '\r', r >= 0x1c && r <= 0x20, r == 0x85, r == 0xa0, r == 0x1680,
		r >= 0x2000 && r <= 0x200a, r == 0x2028, r == 0x2029, r == 0x202f, r == 0x205f, r == 0x3000:
		return true
	}
	return false
}

func pyStrip(s []rune) []rune {
	a, b := 0, len(s)
	for a < b && isSpace(s[a]) {
		a++
	}
	for b > a && isSpace(s[b-1]) {
		b--
	}
	return s[a:b]
}

func pyRstrip(s []rune) []rune {
	b := len(s)
	for b > 0 && isSpace(s[b-1]) {
		b--
	}
	return s[:b]
}

// splitlines is Python's str.splitlines().
func splitlines(s []rune) [][]rune {
	var lines [][]rune
	start := 0
	for i := 0; i < len(s); i++ {
		switch s[i] {
		case '\r':
			lines = append(lines, s[start:i])
			if i+1 < len(s) && s[i+1] == '\n' {
				i++
			}
			start = i + 1
		case '\n', '\v', '\f', 0x1c, 0x1d, 0x1e, 0x85, 0x2028, 0x2029:
			lines = append(lines, s[start:i])
			start = i + 1
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}
