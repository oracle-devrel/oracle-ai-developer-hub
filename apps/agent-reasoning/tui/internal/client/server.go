package client

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const (
	ServerHost = "http://localhost:8080"
)

// ServerClient communicates with server.py
type ServerClient struct {
	baseURL string
	client  *http.Client
}

// GenerateRequest is the request body for /api/generate
type GenerateRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

// GenerateResponse is a single response chunk from /api/generate
type GenerateResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Response  string `json:"response"`
	Done      bool   `json:"done"`
}

// NewServerClient creates a new server client
func NewServerClient() *ServerClient {
	return &ServerClient{
		baseURL: ServerHost,
		client: &http.Client{
			Timeout: 0, // No timeout for streaming
		},
	}
}

// Generate sends a query to the server and returns a channel of response chunks
func (c *ServerClient) Generate(ctx context.Context, model, prompt string) (<-chan GenerateResponse, <-chan error) {
	respChan := make(chan GenerateResponse, 100)
	errChan := make(chan error, 1)

	go func() {
		defer close(respChan)
		defer close(errChan)

		reqBody := GenerateRequest{
			Model:  model,
			Prompt: prompt,
			Stream: true,
		}

		body, err := json.Marshal(reqBody)
		if err != nil {
			errChan <- fmt.Errorf("failed to marshal request: %w", err)
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate", bytes.NewReader(body))
		if err != nil {
			errChan <- fmt.Errorf("failed to create request: %w", err)
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errChan <- fmt.Errorf("failed to send request: %w", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			errChan <- fmt.Errorf("server returned status %d", resp.StatusCode)
			return
		}

		scanner := bufio.NewScanner(resp.Body)
		// Increase buffer size for large responses
		scanner.Buffer(make([]byte, 64*1024), 1024*1024)

		for scanner.Scan() {
			select {
			case <-ctx.Done():
				return
			default:
			}

			line := scanner.Text()
			if line == "" {
				continue
			}

			var genResp GenerateResponse
			if err := json.Unmarshal([]byte(line), &genResp); err != nil {
				// Skip malformed lines
				continue
			}

			respChan <- genResp

			if genResp.Done {
				return
			}
		}

		if err := scanner.Err(); err != nil {
			errChan <- fmt.Errorf("error reading response: %w", err)
		}
	}()

	return respChan, errChan
}

// GenerateSync sends a query and waits for the complete response
func (c *ServerClient) GenerateSync(ctx context.Context, model, prompt string) (string, error) {
	respChan, errChan := c.Generate(ctx, model, prompt)

	var fullResponse string
	for {
		select {
		case resp, ok := <-respChan:
			if !ok {
				return fullResponse, nil
			}
			fullResponse += resp.Response
			if resp.Done {
				return fullResponse, nil
			}
		case err := <-errChan:
			if err != nil {
				return fullResponse, err
			}
		case <-ctx.Done():
			return fullResponse, ctx.Err()
		}
	}
}

// IsHealthy checks if the server is responding
func (c *ServerClient) IsHealthy() bool {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/api/tags", nil)
	if err != nil {
		return false
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
