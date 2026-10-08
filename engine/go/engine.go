package dualengine

import (
	"math"
	"sync/atomic"
	"time"
)

// FailureMode represents an atomic FMEA sub-channel
type FailureMode struct {
	ModeID             string
	Name               string
	CurrentProbability float64
	RuptureThreshold   float64
}

// SystemState captures the full linear algebra state vector and routing weights
type SystemState struct {
	StateVector []float64     // [MemorySaturation, ConnectionSaturation]
	WeightMatrix [][]float64   // Routing Mesh
	EpistemicVariance float64  // Uncertainty fluid volume
}

// DualEngine orchestrates the discrete processing thread and background clock daemon
type DualEngine struct {
	activeState  atomic.Pointer[SystemState]
	SamplingRate time.Duration
	ClockTicker  time.Duration
}

func NewDualEngine(initialState *SystemState, sampleRate, clockRate time.Duration) *DualEngine {
	engine := &DualEngine{
		SamplingRate: sampleRate,
		ClockTicker:  clockRate,
	}
	engine.activeState.Store(initialState)
	return engine
}

// GetState allows safe, non-blocking concurrent reads of the active routing framework
func (e *DualEngine) GetState() *SystemState {
	return e.activeState.Load()
}
