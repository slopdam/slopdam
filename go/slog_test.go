// SPDX-License-Identifier: MIT

package slopdam

import (
	"bytes"
	"encoding/json"
	"errors"
	"log/slog"
	"strings"
	"testing"
	"testing/slogtest"
)

func jsonLines(t *testing.T, buf *bytes.Buffer) []map[string]any {
	t.Helper()
	var out []map[string]any
	for _, line := range strings.Split(strings.TrimSpace(buf.String()), "\n") {
		if line == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			t.Fatal(err)
		}
		out = append(out, m)
	}
	return out
}

func TestHandlerProfiles(t *testing.T) {
	var console, file bytes.Buffer
	reader := slog.New(NewHandler(slog.NewJSONHandler(&console, nil), Options{}))
	dev := slog.New(NewHandler(slog.NewJSONHandler(&file, nil), Options{Profile: "dev"}))
	for _, l := range []*slog.Logger{reader, dev} {
		l.Info("✅ **Saved** 3 rows — done!", "user", "a—b", "note", "✅ kept")
		l.Info("==========")
		l.Error("❌ 업로드 실패 ㅡ 재시도", "err", errors.New("boom — original"))
		l.Warn("⚠️ 디스크 부족 ㅡ 확인")
	}
	var got []string
	for _, m := range jsonLines(t, &console) {
		got = append(got, m["msg"].(string))
	}
	want := []string{"Saved 3 rows: done!", "업로드 실패: 재시도", "디스크 부족: 확인"}
	if strings.Join(got, "|") != strings.Join(want, "|") {
		t.Errorf("reader = %q, want %q", got, want)
	}
	lines := jsonLines(t, &file)
	got = nil
	for _, m := range lines {
		got = append(got, m["msg"].(string))
	}
	want = []string{"[OK] Saved 3 rows - done!", "업로드 실패 - 재시도", "디스크 부족 - 확인"}
	if strings.Join(got, "|") != strings.Join(want, "|") {
		t.Errorf("dev = %q, want %q", got, want)
	}
	if lines[0]["user"] != "a—b" || lines[0]["note"] != "✅ kept" {
		t.Errorf("attributes changed: %v", lines[0])
	}
	if lines[1]["err"] != "boom — original" {
		t.Errorf("error changed: %v", lines[1]["err"])
	}
}

func TestHandlerKeepsSeparatorWithError(t *testing.T) {
	var buf bytes.Buffer
	log := slog.New(NewHandler(slog.NewJSONHandler(&buf, nil), Options{}))
	log.Error("ㅡㅡㅡㅡ", "err", errors.New("boom"))
	if lines := jsonLines(t, &buf); len(lines) != 1 || lines[0]["msg"] != "" {
		t.Errorf("got %v", lines)
	}
}

func TestHandlerWithAttrsAndGroup(t *testing.T) {
	var buf bytes.Buffer
	log := slog.New(NewHandler(slog.NewJSONHandler(&buf, nil), Options{})).With("svc", "api").WithGroup("req")
	log.Info("🚀 Started — ok", "id", 7)
	m := jsonLines(t, &buf)[0]
	if m["msg"] != "Started: ok" || m["svc"] != "api" || m["req"].(map[string]any)["id"] != float64(7) {
		t.Errorf("got %v", m)
	}
}

// TestHandlerContract runs the standard library's handler conformance tests.
func TestHandlerContract(t *testing.T) {
	var buf bytes.Buffer
	h := NewHandler(slog.NewJSONHandler(&buf, nil), Options{})
	results := func() []map[string]any {
		var out []map[string]any
		for _, line := range bytes.Split(buf.Bytes(), []byte("\n")) {
			if len(line) == 0 {
				continue
			}
			var m map[string]any
			if err := json.Unmarshal(line, &m); err != nil {
				t.Fatal(err)
			}
			out = append(out, m)
		}
		return out
	}
	if err := slogtest.TestHandler(h, results); err != nil {
		t.Error(err)
	}
}
