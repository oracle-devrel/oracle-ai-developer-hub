package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ChatMessage represents a single message in the chat
type ChatMessage struct {
	Role    string // "user" or "assistant"
	Content string
}

// Chat represents the main chat panel
type Chat struct {
	viewport     viewport.Model
	messages     []ChatMessage
	streaming    string // Current streaming content
	isStreaming  bool
	agentName    string
	agentID      string
	width        int
	height       int
}

// NewChat creates a new chat component
func NewChat() *Chat {
	vp := viewport.New(60, 20)
	vp.SetContent("")

	return &Chat{
		viewport:    vp,
		messages:    []ChatMessage{},
		streaming:   "",
		isStreaming: false,
		agentName:   "Standard",
		agentID:     "standard",
		width:       60,
		height:      20,
	}
}

// SetSize updates the chat dimensions
func (c *Chat) SetSize(width, height int) {
	c.width = width
	c.height = height
	c.viewport.Width = width - 4  // Account for padding
	c.viewport.Height = height - 4 // Account for title and padding
	c.updateContent()
}

// SetAgent updates the current agent
func (c *Chat) SetAgent(id, name string) {
	c.agentID = id
	c.agentName = name
}

// AddUserMessage adds a user message
func (c *Chat) AddUserMessage(content string) {
	c.messages = append(c.messages, ChatMessage{
		Role:    "user",
		Content: content,
	})
	c.updateContent()
}

// StartStreaming begins streaming mode
func (c *Chat) StartStreaming() {
	c.isStreaming = true
	c.streaming = ""
	c.updateContent()
}

// AppendStreaming appends content to the streaming message
func (c *Chat) AppendStreaming(content string) {
	c.streaming += content
	c.updateContent()
}

// FinishStreaming completes the streaming and saves the message
func (c *Chat) FinishStreaming() {
	if c.streaming != "" {
		c.messages = append(c.messages, ChatMessage{
			Role:    "assistant",
			Content: c.streaming,
		})
	}
	c.streaming = ""
	c.isStreaming = false
	c.updateContent()
}

// CancelStreaming cancels and discards the streaming content
func (c *Chat) CancelStreaming() {
	if c.streaming != "" {
		c.messages = append(c.messages, ChatMessage{
			Role:    "assistant",
			Content: c.streaming + "\n\n[Cancelled]",
		})
	}
	c.streaming = ""
	c.isStreaming = false
	c.updateContent()
}

// Clear clears all messages
func (c *Chat) Clear() {
	c.messages = []ChatMessage{}
	c.streaming = ""
	c.isStreaming = false
	c.updateContent()
}

// IsStreaming returns whether the chat is in streaming mode
func (c *Chat) IsStreaming() bool {
	return c.isStreaming
}

// updateContent updates the viewport content
func (c *Chat) updateContent() {
	var b strings.Builder

	for _, msg := range c.messages {
		if msg.Role == "user" {
			b.WriteString(ChatUserStyle.Render("You: "))
			b.WriteString(msg.Content)
		} else {
			b.WriteString(ChatAssistantStyle.Render("Assistant:"))
			b.WriteString("\n")
			b.WriteString(msg.Content)
		}
		b.WriteString("\n\n")
	}

	// Add streaming content if any
	if c.isStreaming {
		b.WriteString(ChatAssistantStyle.Render("Assistant:"))
		b.WriteString("\n")
		if c.streaming != "" {
			b.WriteString(c.streaming)
		}
		b.WriteString(ChatStreamingStyle.Render(" ●"))
	}

	c.viewport.SetContent(b.String())
	c.viewport.GotoBottom()
}

// Update handles viewport updates
func (c *Chat) Update(msg tea.Msg) (*Chat, tea.Cmd) {
	var cmd tea.Cmd
	c.viewport, cmd = c.viewport.Update(msg)
	return c, cmd
}

// View renders the chat panel
func (c *Chat) View() string {
	title := ChatTitleStyle.Render(fmt.Sprintf("[%s] %s", c.agentID, c.agentName))
	separator := lipgloss.NewStyle().Foreground(ColorMuted).Render(strings.Repeat("─", c.width-4))

	content := lipgloss.JoinVertical(lipgloss.Left,
		title,
		separator,
		c.viewport.View(),
	)

	return ChatPanelStyle.Width(c.width).Height(c.height).Render(content)
}
