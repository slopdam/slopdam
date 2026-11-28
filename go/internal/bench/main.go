// SPDX-License-Identifier: MIT

// Command bench times Sanitizer.Clean on each line of a JSON-lines file of {"input": ...} rows and
// prints the per-line times in nanoseconds as a JSON array. scripts/bench_lines.py runs it.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"time"

	slopdam "github.com/slopdam/slopdam/go"
)

func main() {
	f, err := os.Open(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var lines []string
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	for sc.Scan() {
		var row struct{ Input string }
		if json.Unmarshal(sc.Bytes(), &row) == nil {
			lines = append(lines, row.Input)
		}
	}
	s, err := slopdam.New(slopdam.Options{Profile: os.Args[2], Level: os.Args[3]})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	for _, l := range lines { // warm up
		s.Clean(l)
	}
	ns := make([]int64, len(lines))
	for i, l := range lines {
		t := time.Now()
		s.Clean(l)
		ns[i] = time.Since(t).Nanoseconds()
	}
	json.NewEncoder(os.Stdout).Encode(ns)
}
