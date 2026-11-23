// SPDX-License-Identifier: MIT

package slopdam

import (
	"context"
	"log/slog"
)

// Handler is a slog.Handler that cleans the message of every record before passing it on.
// Attributes are structured data and stay as they are. A record whose message was only a
// separator line is dropped, unless it carries an error.
//
//	console := slopdam.NewHandler(slog.NewTextHandler(os.Stderr, nil), slopdam.Options{})
//	file := slopdam.NewHandler(slog.NewJSONHandler(f, nil), slopdam.Options{Profile: "dev"})
//
// Each Handler has its own profile, so a console logger and a file logger can differ.
type Handler struct {
	next slog.Handler
	s    *Sanitizer
}

// NewHandler wraps next. It panics on invalid options, like MustNew.
func NewHandler(next slog.Handler, o Options) *Handler {
	return &Handler{next: next, s: MustNew(o)}
}

// Enabled reports whether the wrapped handler handles records at the level.
func (h *Handler) Enabled(ctx context.Context, level slog.Level) bool {
	return h.next.Enabled(ctx, level)
}

// Handle cleans the message and passes a copy of the record to the wrapped handler.
func (h *Handler) Handle(ctx context.Context, r slog.Record) error {
	msg := h.s.CleanLevel(r.Message, slogLevel(r.Level))
	if msg == "" && r.Message != "" && !hasError(r) {
		return nil // only a separator line
	}
	out := slog.NewRecord(r.Time, r.Level, msg, r.PC)
	r.Attrs(func(a slog.Attr) bool {
		out.AddAttrs(a)
		return true
	})
	return h.next.Handle(ctx, out)
}

// WithAttrs returns a Handler whose wrapped handler has the attributes.
func (h *Handler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return &Handler{next: h.next.WithAttrs(attrs), s: h.s}
}

// WithGroup returns a Handler whose wrapped handler opens the group.
func (h *Handler) WithGroup(name string) slog.Handler {
	return &Handler{next: h.next.WithGroup(name), s: h.s}
}

// slogLevel maps slog levels to slopdam's (Python logging) scale.
func slogLevel(l slog.Level) int {
	switch {
	case l >= slog.LevelError:
		return LevelError
	case l >= slog.LevelWarn:
		return LevelWarning
	case l >= slog.LevelInfo:
		return LevelInfo
	}
	return LevelDebug
}

func hasError(r slog.Record) bool {
	found := false
	r.Attrs(func(a slog.Attr) bool {
		if _, ok := a.Value.Any().(error); ok {
			found = true
			return false
		}
		return true
	})
	return found
}
