// SPDX-License-Identifier: MIT

package slopdam

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"testing"
)

type conformanceCase struct {
	Input   string `json:"input"`
	Reader  string `json:"reader"`
	Dev     string `json:"dev"`
	Options struct {
		Level      string `json:"level"`
		DashInline string `json:"dash_inline"`
		LogLevel   string `json:"log_level"`
	} `json:"options"`
}

// TestConformance runs every case of ../spec/conformance.json for both profiles.
func TestConformance(t *testing.T) {
	data, err := os.ReadFile("../spec/conformance.json")
	if err != nil {
		t.Fatal(err)
	}
	var doc struct {
		Groups []struct {
			ID    string            `json:"id"`
			Cases []conformanceCase `json:"cases"`
		} `json:"groups"`
	}
	if err := json.Unmarshal(data, &doc); err != nil {
		t.Fatal(err)
	}
	n := 0
	for _, g := range doc.Groups {
		for i, c := range g.Cases {
			for _, profile := range []string{"reader", "dev"} {
				want := c.Reader
				if profile == "dev" {
					want = c.Dev
				}
				s := MustNew(Options{Profile: profile, Level: c.Options.Level, DashInline: c.Options.DashInline})
				level := LevelNone
				if c.Options.LogLevel != "" {
					level = levelNumber(c.Options.LogLevel)
				}
				t.Run(fmt.Sprintf("%s/%d/%s", g.ID, i, profile), func(t *testing.T) {
					if got := s.CleanLevel(c.Input, level); got != want {
						t.Errorf("Clean(%q) = %q, want %q", c.Input, got, want)
					}
					if got := s.CleanLevel(want, level); got != want {
						t.Errorf("not idempotent: Clean(%q) = %q", want, got)
					}
				})
				n++
			}
		}
	}
	if n < 200 {
		t.Fatalf("only %d conformance checks ran", n)
	}
}

func TestOptions(t *testing.T) {
	if got := Clean("완료 ㅡ 다음"); got != "완료: 다음" {
		t.Errorf("Clean = %q", got)
	}
	comma := MustNew(Options{DashInline: "comma"})
	if got := comma.Clean("완료 ㅡ 다음"); got != "완료, 다음" {
		t.Errorf("comma = %q", got)
	}
	dev := MustNew(Options{Profile: "dev"})
	if got := dev.CleanLevel("❌ 실패", LevelError); got != "실패" {
		t.Errorf("dev at error = %q", got)
	}
	if got := MustNew(Options{Disable: []string{"emoji"}}).Clean("✅ 완료 ㅡ 다음"); got != "✅ 완료: 다음" {
		t.Errorf("disable = %q", got)
	}
	for _, o := range []Options{{Profile: "nope"}, {Level: "max"}, {DashInline: "semicolon"}} {
		if _, err := New(o); err == nil {
			t.Errorf("New(%+v) did not fail", o)
		}
	}
}

func TestFindings(t *testing.T) {
	text := `log.Info("✅ **Saved** 3 rows — done! 🎉")`
	found := MustNew(Options{}).Findings(text)
	var got []string
	for _, f := range found {
		fix := "<report>"
		if f.Fix != nil {
			fix = *f.Fix
		}
		got = append(got, f.RuleID+" "+f.Text+" -> "+fix)
		if strings.TrimSpace(text[f.Start:f.End]) != f.Text {
			t.Errorf("span %d:%d = %q, want %q", f.Start, f.End, text[f.Start:f.End], f.Text)
		}
	}
	want := []string{"emoji.pictograph ✅ -> ", "md.emphasis **Saved** -> Saved", "dash.run — -> : ", "emoji.pictograph 🎉 -> "}
	if strings.Join(got, "|") != strings.Join(want, "|") {
		t.Errorf("findings = %q, want %q", got, want)
	}
	if f := MustNew(Options{}).Findings("Let's go"); len(f) != 1 || f[0].Fix != nil {
		t.Errorf("report-only finding = %+v", f)
	}
}
