module github.com/slopdam/slopdam/go/vet

go 1.26.0

require (
	github.com/slopdam/slopdam/go v0.5.0
	golang.org/x/tools v0.52.0
)

require (
	github.com/dlclark/regexp2 v1.12.0 // indirect
	golang.org/x/mod v0.42.0 // indirect
	golang.org/x/sync v0.24.0 // indirect
)

// v0.1.0 was tagged on the commit before go.mod dropped its replace directive, so
// `go install ...@v0.1.0` refuses it. Use v0.1.1 or later.
retract v0.1.0
