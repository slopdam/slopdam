// SPDX-License-Identifier: MIT

// Command slopdamvet runs the slopdam analyzer on Go packages, on its own or as go vet's tool.
//
//	slopdamvet ./...
//	slopdamvet -fix ./...
//	go vet -vettool=$(which slopdamvet) ./...
package main

import (
	"golang.org/x/tools/go/analysis/singlechecker"

	"github.com/slopdam/slopdam/go/vet"
)

func main() { singlechecker.Main(vet.Analyzer) }
