# LangGraph Webhook Server

This project integrates a LangGraph agent with a Flask web server to handle webhook events.

## Features

- LangGraph agent with tools for search and human assistance
- Flask web server with two endpoints:
  - `GET /`: Returns a status message
  - `POST /events`: Accepts webhook payloads and prints them

## Setup

1. Make sure all dependencies are installed:
   ```
   pip install -r requirements.txt
   ```

2. Set up your environment variables in a `.env` file:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

## Usage

### CLI Mode

Run the application in CLI mode to interact with the agent directly:

```
python main.py
```

### Server Mode

Run the application in server mode to start the Flask web server:

```
python main.py server
```

The server will start on `http://0.0.0.0:5000/`.

### Testing Webhooks

You can test the webhook endpoint using curl:

```
curl -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from webhook", "data": {"key": "value"}}'
```

## Customizing Webhook Handling

To process webhook payloads with the LangGraph agent, uncomment and modify the code in the `webhook_handler()` function in `main.py`.
