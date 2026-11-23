module github.com/slopdam/slopdam/go/vet

go 1.26.0

require (
	github.com/slopdam/slopdam/go v0.1.0
	golang.org/x/tools v0.52.0
)

require (
	github.com/dlclark/regexp2 v1.12.0 // indirect
	golang.org/x/mod v0.42.0 // indirect
	golang.org/x/sync v0.24.0 // indirect
)

// Built against the module in the parent directory; released with the same version tag.
replace github.com/slopdam/slopdam/go => ../
