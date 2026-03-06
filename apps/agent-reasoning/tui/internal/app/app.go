package app

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"agent-reasoning-tui/internal/client"
	"agent-reasoning-tui/internal/ui"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Focus represents which component has focus
type Focus int

const (
	FocusSidebar Focus = iota
	FocusInput
)

// Messages for async operations
type (
	serverConnectedMsg    struct{}
	serverDisconnectedMsg struct{}
	modelsLoadedMsg       struct{ models []string }
	modelsErrorMsg        struct{ err error }
	streamChunkMsg        struct {
		agentID string
		content string
	}
	streamDoneMsg struct {
		agentID  string
		duration float64
	}
	streamErrorMsg struct {
		agentID string
		err     error
	}
	arenaCompleteMsg     struct{}
	benchmarkCompleteMsg struct{ err error }
)

// KeyMap defines the keybindings
type KeyMap struct {
	Up     key.Binding
	Down   key.Binding
	Enter  key.Binding
	Tab    key.Binding
	Escape key.Binding
	Quit   key.Binding
}

// DefaultKeyMap returns the default keybindings
func DefaultKeyMap() KeyMap {
	return KeyMap{
		Up: key.NewBinding(
			key.WithKeys("up", "k"),
			key.WithHelp("↑/k", "up"),
		),
		Down: key.NewBinding(
			key.WithKeys("down", "j"),
			key.WithHelp("↓/j", "down"),
		),
		Enter: key.NewBinding(
			key.WithKeys("enter"),
			key.WithHelp("enter", "select/submit"),
		),
		Tab: key.NewBinding(
			key.WithKeys("tab"),
			key.WithHelp("tab", "switch focus"),
		),
		Escape: key.NewBinding(
			key.WithKeys("esc"),
			key.WithHelp("esc", "cancel"),
		),
		Quit: key.NewBinding(
			key.WithKeys("ctrl+c", "q"),
			key.WithHelp("q/ctrl+c", "quit"),
		),
	}
}

// Model is the main application model
type Model struct {
	// UI components
	header        *ui.Header
	sidebar       *ui.Sidebar
	chat          *ui.Chat
	input         *ui.Input
	arena         *ui.Arena
	modelSelector *ui.ModelSelector

	// Clients
	serverClient *client.ServerClient
	ollamaClient *client.OllamaClient

	// State
	focus         Focus
	currentModel  string
	currentAgent  string
	connected     bool
	width         int
	height        int
	quitting      bool

	// Streaming control
	streamCancel   context.CancelFunc
	streamRespChan <-chan client.GenerateResponse
	streamErrChan  <-chan error
	streamStart    time.Time

	// Keys
	keys KeyMap
}

// New creates a new application model
func New() *Model {
	sidebar := ui.NewSidebar()
	chat := ui.NewChat()
	input := ui.NewInput()

	return &Model{
		header:        ui.NewHeader(),
		sidebar:       sidebar,
		chat:          chat,
		input:         input,
		arena:         ui.NewArena(),
		modelSelector: ui.NewModelSelector(),
		serverClient:  client.NewServerClient(),
		ollamaClient:  client.NewOllamaClient(),
		focus:         FocusSidebar,
		currentModel:  "gemma3:latest",
		currentAgent:  "standard",
		connected:     false,
		keys:          DefaultKeyMap(),
	}
}

// Init initializes the application
func (m *Model) Init() tea.Cmd {
	return tea.Batch(
		m.checkConnection(),
		tea.EnterAltScreen,
	)
}

// checkConnection checks if the server is healthy
func (m *Model) checkConnection() tea.Cmd {
	return func() tea.Msg {
		if m.serverClient.IsHealthy() {
			return serverConnectedMsg{}
		}
		return serverDisconnectedMsg{}
	}
}

// loadModels fetches available models from Ollama
func (m *Model) loadModels() tea.Cmd {
	return func() tea.Msg {
		models, err := m.ollamaClient.ListModels()
		if err != nil {
			return modelsErrorMsg{err: err}
		}
		return modelsLoadedMsg{models: models}
	}
}

// startStream initiates a streaming query and returns the first chunk.
// On subsequent calls (empty query), it reads the next chunk from stored channels.
func (m *Model) startStream(agentID, query string) tea.Cmd {
	// If query is non-empty, start a new request and store the channels
	if query != "" {
		ctx, cancel := context.WithCancel(context.Background())
		m.streamCancel = cancel
		m.streamStart = time.Now()

		modelWithStrategy := fmt.Sprintf("%s+%s", m.currentModel, agentID)
		m.streamRespChan, m.streamErrChan = m.serverClient.Generate(ctx, modelWithStrategy, query)
	}

	// Capture channel refs for the closure
	respChan := m.streamRespChan
	errChan := m.streamErrChan
	startTime := m.streamStart

	return func() tea.Msg {
		if respChan == nil {
			return streamDoneMsg{agentID: agentID, duration: 0}
		}
		for {
			select {
			case resp, ok := <-respChan:
				if !ok {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
				if resp.Response != "" {
					return streamChunkMsg{agentID: agentID, content: resp.Response}
				}
				if resp.Done {
					return streamDoneMsg{agentID: agentID, duration: time.Since(startTime).Seconds()}
				}
			case err := <-errChan:
				if err != nil {
					return streamErrorMsg{agentID: agentID, err: err}
				}
			}
		}
	}
}

// startArena starts all agents in parallel
func (m *Model) startArena(query string) tea.Cmd {
	return func() tea.Msg {
		// This will be handled by spawning multiple goroutines
		return nil
	}
}

// Update handles messages
func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		return m.handleKeyMsg(msg)

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.updateSizes()

	case serverConnectedMsg:
		m.connected = true
		m.header.SetConnected(true)

	case serverDisconnectedMsg:
		m.connected = false
		m.header.SetConnected(false)
		// Retry connection
		cmds = append(cmds, tea.Tick(2*time.Second, func(time.Time) tea.Msg {
			return m.checkConnection()()
		}))

	case modelsLoadedMsg:
		m.modelSelector.SetModels(msg.models)

	case modelsErrorMsg:
		m.modelSelector.SetError(msg.err.Error())

	case streamChunkMsg:
		if m.arena.IsActive() {
			m.arena.AppendCellContent(msg.agentID, msg.content)
		} else {
			m.chat.AppendStreaming(msg.content)
		}
		// Continue streaming
		cmds = append(cmds, m.startStream(msg.agentID, ""))

	case streamDoneMsg:
		if m.arena.IsActive() {
			m.arena.SetCellStatus(msg.agentID, ui.ArenaDone)
			m.arena.SetCellDuration(msg.agentID, msg.duration)
		} else {
			m.chat.FinishStreaming()
		}

	case streamErrorMsg:
		if m.arena.IsActive() {
			m.arena.SetCellError(msg.agentID, msg.err.Error())
		} else {
			m.chat.AppendStreaming(fmt.Sprintf("\n\n[Error: %v]", msg.err))
			m.chat.FinishStreaming()
		}

	case benchmarkCompleteMsg:
		// Returned from benchmark CLI - just continue
		// Errors would have been displayed by the CLI itself
	}

	return m, tea.Batch(cmds...)
}

// handleKeyMsg handles keyboard input
func (m *Model) handleKeyMsg(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Handle model selector if active
	if m.modelSelector.IsActive() {
		return m.handleModelSelectorKey(msg)
	}

	// Handle arena mode if active
	if m.arena.IsActive() {
		return m.handleArenaKey(msg)
	}

	// Global keys
	switch {
	case key.Matches(msg, m.keys.Quit):
		if !m.chat.IsStreaming() {
			m.quitting = true
			return m, tea.Quit
		}
		// Cancel streaming on first quit attempt
		if m.streamCancel != nil {
			m.streamCancel()
		}
		m.chat.CancelStreaming()
		return m, nil

	case key.Matches(msg, m.keys.Escape):
		if m.chat.IsStreaming() {
			if m.streamCancel != nil {
				m.streamCancel()
			}
			m.chat.CancelStreaming()
		}
		return m, nil

	case key.Matches(msg, m.keys.Tab):
		m.toggleFocus()
		return m, nil
	}

	// Route to focused component
	if m.focus == FocusSidebar {
		return m.handleSidebarKey(msg)
	}
	return m.handleInputKey(msg)
}

// handleSidebarKey handles keys when sidebar is focused
func (m *Model) handleSidebarKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch {
	case key.Matches(msg, m.keys.Up):
		m.sidebar.MoveUp()
	case key.Matches(msg, m.keys.Down):
		m.sidebar.MoveDown()
	case key.Matches(msg, m.keys.Enter):
		return m.handleSidebarSelect()
	}
	return m, nil
}

// handleSidebarSelect handles selecting an item in the sidebar
func (m *Model) handleSidebarSelect() (tea.Model, tea.Cmd) {
	selected := m.sidebar.Selected()

	switch selected {
	case "arena":
		// Switch to arena mode - focus input for query
		m.focus = FocusInput
		m.input.Focus()
		m.sidebar.SetFocused(false)
		// Mark that we want arena mode when query is submitted
		m.currentAgent = "arena"
		return m, nil

	case "benchmark":
		// Launch benchmark CLI
		return m, m.runBenchmarkCLI()

	case "model":
		// Show model selector
		m.modelSelector.Show()
		m.modelSelector.SetLoading(true)
		return m, m.loadModels()

	default:
		// Select an agent
		m.currentAgent = selected
		item := m.sidebar.SelectedItem()
		m.chat.SetAgent(selected, item.Label)
		m.chat.Clear()
		// Focus input
		m.focus = FocusInput
		m.input.Focus()
		m.sidebar.SetFocused(false)
	}

	return m, nil
}

// handleInputKey handles keys when input is focused
func (m *Model) handleInputKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch {
	case key.Matches(msg, m.keys.Enter):
		query := m.input.Value()
		if query == "" {
			return m, nil
		}

		if m.currentAgent == "arena" {
			// Start arena mode
			m.arena.Start(query)
			m.input.Reset()
			return m, m.startArenaRun(query)
		}

		// Normal chat mode
		m.chat.AddUserMessage(query)
		m.chat.StartStreaming()
		m.input.Reset()

		return m, m.startStream(m.currentAgent, query)

	default:
		// Pass to input component
		var cmd tea.Cmd
		m.input, cmd = m.input.Update(msg)
		return m, cmd
	}
}

// handleModelSelectorKey handles keys in model selector
func (m *Model) handleModelSelectorKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch {
	case key.Matches(msg, m.keys.Up):
		m.modelSelector.MoveUp()
	case key.Matches(msg, m.keys.Down):
		m.modelSelector.MoveDown()
	case key.Matches(msg, m.keys.Enter):
		selected := m.modelSelector.Selected()
		if selected != "" {
			m.currentModel = selected
			m.header.SetModel(selected)
		}
		m.modelSelector.Hide()
	case key.Matches(msg, m.keys.Escape):
		m.modelSelector.Hide()
	}
	return m, nil
}

// handleArenaKey handles keys in arena mode
func (m *Model) handleArenaKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch {
	case key.Matches(msg, m.keys.Escape):
		m.arena.Stop()
		// Cancel all streams if any
		if m.streamCancel != nil {
			m.streamCancel()
		}
	case key.Matches(msg, m.keys.Quit):
		m.arena.Stop()
		if m.streamCancel != nil {
			m.streamCancel()
		}
		m.quitting = true
		return m, tea.Quit
	}
	return m, nil
}

// toggleFocus switches focus between sidebar and input
func (m *Model) toggleFocus() {
	if m.focus == FocusSidebar {
		m.focus = FocusInput
		m.sidebar.SetFocused(false)
		m.input.Focus()
	} else {
		m.focus = FocusSidebar
		m.sidebar.SetFocused(true)
		m.input.Blur()
	}
}

// updateSizes updates component sizes based on window size
func (m *Model) updateSizes() {
	headerHeight := 3
	inputHeight := 3
	sidebarWidth := ui.SidebarWidth + 2

	contentHeight := m.height - headerHeight - inputHeight
	chatWidth := m.width - sidebarWidth

	m.header.SetWidth(m.width)
	m.sidebar.SetHeight(contentHeight)
	m.chat.SetSize(chatWidth, contentHeight)
	m.input.SetWidth(m.width)
	m.arena.SetSize(m.width, m.height-headerHeight)
	m.modelSelector.SetSize(50, 20)
}


// startArenaRun starts all agents in arena mode
func (m *Model) startArenaRun(query string) tea.Cmd {
	agents := ui.DefaultAgents()

	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())
		m.streamCancel = cancel

		// Create channels for results
		type arenaResult struct {
			agentID  string
			content  string
			duration float64
			err      error
		}
		results := make(chan arenaResult, len(agents))

		// Start all agents concurrently
		for _, agent := range agents {
			go func(agentID string) {
				modelWithStrategy := fmt.Sprintf("%s+%s", m.currentModel, agentID)
				startTime := time.Now()

				m.arena.SetCellStatus(agentID, ui.ArenaRunning)

				content, err := m.serverClient.GenerateSync(ctx, modelWithStrategy, query)
				duration := time.Since(startTime).Seconds()

				results <- arenaResult{
					agentID:  agentID,
					content:  content,
					duration: duration,
					err:      err,
				}
			}(agent.ID)
		}

		// Collect results
		for i := 0; i < len(agents); i++ {
			result := <-results
			if result.err != nil {
				m.arena.SetCellError(result.agentID, result.err.Error())
			} else {
				m.arena.SetCellContent(result.agentID, result.content)
				m.arena.SetCellStatus(result.agentID, ui.ArenaDone)
				m.arena.SetCellDuration(result.agentID, result.duration)
			}
		}

		return arenaCompleteMsg{}
	}
}

// runBenchmarkCLI launches the Python benchmark CLI
func (m *Model) runBenchmarkCLI() tea.Cmd {
	c := exec.Command("python", "agent_cli.py", "--benchmark")
	return tea.ExecProcess(c, func(err error) tea.Msg {
		return benchmarkCompleteMsg{err: err}
	})
}

// View renders the application
func (m *Model) View() string {
	if m.quitting {
		return "Goodbye!\n"
	}

	// Arena mode view
	if m.arena.IsActive() {
		return lipgloss.JoinVertical(lipgloss.Left,
			m.header.View(),
			m.arena.View(),
		)
	}

	// Normal view
	header := m.header.View()
	sidebar := m.sidebar.View()
	chat := m.chat.View()
	input := m.input.View()

	// Join sidebar and chat horizontally
	mainContent := lipgloss.JoinHorizontal(lipgloss.Top, sidebar, chat)

	// Join all vertically
	view := lipgloss.JoinVertical(lipgloss.Left, header, mainContent, input)

	// Overlay model selector if active
	if m.modelSelector.IsActive() {
		selectorView := m.modelSelector.View()
		// Center the selector
		x := (m.width - 50) / 2
		y := (m.height - 20) / 2
		view = placeOverlay(x, y, selectorView, view)
	}

	return view
}

// placeOverlay places an overlay on top of a background
func placeOverlay(x, y int, overlay, background string) string {
	bgLines := strings.Split(background, "\n")
	overlayLines := strings.Split(overlay, "\n")

	for i, line := range overlayLines {
		bgY := y + i
		if bgY >= 0 && bgY < len(bgLines) {
			bgLine := bgLines[bgY]
			// Replace portion of background with overlay
			if x >= 0 && x < len(bgLine) {
				before := ""
				if x > 0 {
					before = bgLine[:x]
				}
				after := ""
				endX := x + lipgloss.Width(line)
				if endX < len(bgLine) {
					after = bgLine[endX:]
				}
				bgLines[bgY] = before + line + after
			}
		}
	}

	return strings.Join(bgLines, "\n")
}
