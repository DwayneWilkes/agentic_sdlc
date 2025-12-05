#!/usr/bin/env node

/**
 * NATS Chat MCP Server
 *
 * Provides a simple chat interface over NATS JetStream for agent communication.
 * Agents can set handles, send messages, and read message history.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { connect, NatsConnection, JetStreamClient, JetStreamManager, StorageType } from "nats";

// Global state
let currentHandle: string | null = null;
let nc: NatsConnection | null = null;
let js: JetStreamClient | null = null;
let jsm: JetStreamManager | null = null;

// Channel definitions
const CHANNELS = {
  roadmap: "Discussion about project roadmap and planning",
  "parallel-work": "Coordination for parallel work among agents",
  errors: "Error reporting and troubleshooting",
} as const;

type ChannelName = keyof typeof CHANNELS;

const STREAM_PREFIX = "CHAT_";
const SUBJECT_PREFIX = "chat.";

/**
 * Initialize NATS connection and JetStream
 */
async function initNATS(): Promise<void> {
  if (nc) return; // Already connected

  try {
    nc = await connect({
      servers: process.env.NATS_URL || "nats://localhost:4222",
      name: "nats-chat-mcp-server",
    });

    console.error(`Connected to NATS at ${nc.getServer()}`);

    js = nc.jetstream();
    jsm = await nc.jetstreamManager();

    // Create streams for each channel
    for (const channel of Object.keys(CHANNELS) as ChannelName[]) {
      const streamName = `${STREAM_PREFIX}${channel.toUpperCase().replace("-", "_")}`;
      const subject = `${SUBJECT_PREFIX}${channel}`;

      try {
        await jsm.streams.info(streamName);
        console.error(`Stream ${streamName} already exists`);
      } catch (err) {
        // Stream doesn't exist, create it
        await jsm.streams.add({
          name: streamName,
          subjects: [subject],
          storage: StorageType.Memory,
          retention: "limits",
          max_age: 24 * 60 * 60 * 1e9, // 24 hours in nanoseconds
          max_msgs: 10000,
          max_bytes: 10 * 1024 * 1024, // 10MB
        });
        console.error(`Created stream ${streamName} for channel ${channel}`);
      }
    }
  } catch (error) {
    console.error("Failed to connect to NATS:", error);
    throw error;
  }
}

/**
 * Set agent handle (username)
 */
async function setHandle(handle: string): Promise<string> {
  if (!handle || handle.trim() === "") {
    throw new Error("Handle cannot be empty");
  }

  currentHandle = handle.trim();
  return `Handle set to: ${currentHandle}`;
}

/**
 * Get current agent handle
 */
async function getMyHandle(): Promise<string> {
  if (!currentHandle) {
    throw new Error("No handle set. Use set_handle first.");
  }
  return currentHandle;
}

/**
 * List available channels
 */
async function listChannels(): Promise<string> {
  const channelList = Object.entries(CHANNELS)
    .map(([name, description]) => `- **${name}**: ${description}`)
    .join("\n");

  return `Available channels:\n\n${channelList}`;
}

/**
 * Send a message to a channel
 */
async function sendMessage(channel: string, message: string): Promise<string> {
  if (!currentHandle) {
    throw new Error("No handle set. Use set_handle first.");
  }

  if (!(channel in CHANNELS)) {
    throw new Error(`Invalid channel: ${channel}. Valid channels: ${Object.keys(CHANNELS).join(", ")}`);
  }

  if (!message || message.trim() === "") {
    throw new Error("Message cannot be empty");
  }

  await initNATS();

  const subject = `${SUBJECT_PREFIX}${channel}`;
  const payload = {
    handle: currentHandle,
    message: message.trim(),
    timestamp: new Date().toISOString(),
  };

  if (!js) throw new Error("JetStream not initialized");

  await js.publish(subject, new TextEncoder().encode(JSON.stringify(payload)));

  return `Message sent to ${channel} by ${currentHandle}`;
}

/**
 * Read messages from a channel
 */
async function readMessages(channel: string, limit: number = 50): Promise<string> {
  if (!(channel in CHANNELS)) {
    throw new Error(`Invalid channel: ${channel}. Valid channels: ${Object.keys(CHANNELS).join(", ")}`);
  }

  if (limit < 1 || limit > 1000) {
    throw new Error("Limit must be between 1 and 1000");
  }

  await initNATS();

  const streamName = `${STREAM_PREFIX}${channel.toUpperCase().replace("-", "_")}`;

  if (!jsm || !js) throw new Error("JetStream not initialized");

  try {
    const stream = await jsm.streams.info(streamName);
    const messageCount = stream.state.messages;

    if (messageCount === 0) {
      return `No messages in channel: ${channel}`;
    }

    // Create consumer to read messages
    const consumer = await js.consumers.get(streamName);
    const messages: string[] = [];

    const iter = await consumer.fetch({ max_messages: Math.min(limit, messageCount) });

    for await (const msg of iter) {
      try {
        const data = JSON.parse(new TextDecoder().decode(msg.data));
        messages.push(`[${data.timestamp}] ${data.handle}: ${data.message}`);
        msg.ack();
      } catch (err) {
        console.error("Failed to parse message:", err);
      }
    }

    if (messages.length === 0) {
      return `No messages in channel: ${channel}`;
    }

    return `Messages from ${channel} (${messages.length}):\n\n${messages.join("\n")}`;
  } catch (error) {
    throw new Error(`Failed to read messages: ${error}`);
  }
}

/**
 * Create and start the MCP server
 */
async function main() {
  const server = new Server(
    {
      name: "nats-chat-mcp-server",
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // Define tools
  const tools: Tool[] = [
    {
      name: "set_handle",
      description: "Set your agent handle (username) for chat. Must be called before sending messages.",
      inputSchema: {
        type: "object",
        properties: {
          handle: {
            type: "string",
            description: "Your agent handle/username",
          },
        },
        required: ["handle"],
      },
    },
    {
      name: "get_my_handle",
      description: "Get your current agent handle",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "list_channels",
      description: "List available chat channels",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "send_message",
      description: "Send a message to a chat channel",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: `Channel name (${Object.keys(CHANNELS).join(", ")})`,
            enum: Object.keys(CHANNELS),
          },
          message: {
            type: "string",
            description: "Message to send",
          },
        },
        required: ["channel", "message"],
      },
    },
    {
      name: "read_messages",
      description: "Read recent messages from a channel",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: `Channel name (${Object.keys(CHANNELS).join(", ")})`,
            enum: Object.keys(CHANNELS),
          },
          limit: {
            type: "number",
            description: "Maximum number of messages to retrieve (1-1000, default: 50)",
            minimum: 1,
            maximum: 1000,
            default: 50,
          },
        },
        required: ["channel"],
      },
    },
  ];

  // List tools handler
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools,
  }));

  // Call tool handler
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "set_handle": {
          const result = await setHandle(args.handle as string);
          return { content: [{ type: "text", text: result }] };
        }

        case "get_my_handle": {
          const result = await getMyHandle();
          return { content: [{ type: "text", text: result }] };
        }

        case "list_channels": {
          const result = await listChannels();
          return { content: [{ type: "text", text: result }] };
        }

        case "send_message": {
          const result = await sendMessage(
            args.channel as string,
            args.message as string
          );
          return { content: [{ type: "text", text: result }] };
        }

        case "read_messages": {
          const result = await readMessages(
            args.channel as string,
            args.limit as number || 50
          );
          return { content: [{ type: "text", text: result }] };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        content: [{ type: "text", text: `Error: ${errorMessage}` }],
        isError: true,
      };
    }
  });

  // Start server
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("NATS Chat MCP Server running on stdio");

  // Cleanup on exit
  process.on("SIGINT", async () => {
    if (nc) {
      await nc.close();
    }
    process.exit(0);
  });
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
