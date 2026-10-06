import express from "express";
import cors from "cors";

import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";


const app = express();

const PORT = 8787;

const MCP_URL =
  "https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp";


app.use(cors());
app.use(express.json());


let client = null;


async function getClient() {
  if (client) {
    return client;
  }

  client = new Client({
    name: "relay-web-bridge",
    version: "1.0.0",
  });

  const transport =
    new StreamableHTTPClientTransport(
      new URL(MCP_URL),
    );

  await client.connect(transport);

  return client;
}


function parseTextItem(text) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}


function parseToolResult(result) {
  if (!result) {
    return null;
  }

  if (result.isError) {
    throw new Error(
      "Relay MCP tool returned an error.",
    );
  }

  const textItems =
    result.content?.filter(
      (item) =>
        item.type === "text",
    ) ?? [];

  if (textItems.length === 0) {
    return result;
  }

  const parsedItems =
    textItems.map(
      (item) =>
        parseTextItem(item.text),
    );

  /*
   * Most Relay tools return one JSON object.
   */
  if (parsedItems.length === 1) {
    return parsedItems[0];
  }

  /*
   * Some tools, especially the audit-log tool,
   * can return multiple JSON text blocks.
   *
   * Return them as an array instead of trying
   * to join them into invalid JSON.
   */
  const allObjects =
    parsedItems.every(
      (item) =>
        typeof item === "object" &&
        item !== null,
    );

  if (allObjects) {
    return parsedItems;
  }

  return {
    text: textItems
      .map((item) => item.text)
      .join("\n"),
  };
}


app.get(
  "/api/health",
  async (_req, res) => {
    try {
      const mcp =
        await getClient();

      const tools =
        await mcp.listTools();

      return res.json({
        status: "ok",
        bridge:
          "relay-web-bridge",
        mcpEndpoint:
          MCP_URL,
        tools:
          tools.tools.map(
            (tool) =>
              tool.name,
          ),
      });
    } catch (error) {
      console.error(
        "Health check failed:",
        error,
      );

      client = null;

      return res
        .status(500)
        .json({
          status: "error",

          message:
            error instanceof Error
              ? error.message
              : "Unable to connect to Relay MCP.",
        });
    }
  },
);


app.post(
  "/api/tool",
  async (req, res) => {
    const {
      name,
      arguments: args = {},
    } = req.body ?? {};

    if (!name) {
      return res
        .status(400)
        .json({
          success: false,
          error:
            "Tool name is required.",
        });
    }

    try {
      const mcp =
        await getClient();

      const result =
        await mcp.callTool({
          name,
          arguments: args,
        });

      const parsed =
        parseToolResult(
          result,
        );

      return res.json({
        success: true,
        tool: name,
        result: parsed,
      });
    } catch (error) {
      console.error(
        `Tool ${name} failed:`,
        error,
      );

      client = null;

      return res
        .status(500)
        .json({
          success: false,
          tool: name,

          error:
            error instanceof Error
              ? error.message
              : "Unknown MCP error.",
        });
    }
  },
);


app.listen(
  PORT,
  () => {
    console.log();

    console.log(
      `Relay bridge running at http://localhost:${PORT}`,
    );

    console.log(
      `Relay MCP endpoint: ${MCP_URL}`,
    );

    console.log();
  },
);