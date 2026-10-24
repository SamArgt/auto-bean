import type { App } from "@modelcontextprotocol/ext-apps";
import type { OpenAIExtensions } from "@openai/mcp-extensions/app";
import type { Bridge } from "./types";
export function createBridge(
  app: Pick<App, "callServerTool">,
  extensions: Pick<OpenAIExtensions, "message"> &
    Partial<Pick<OpenAIExtensions, "files">>,
): Bridge {
  return {
    async openFile(path: string) {
      const files = extensions.files;
      if (!files)
        throw new Error(
          "This host cannot open local files. Use the saved path.",
        );
      await files.open(path);
    },
    async call<T>(name: string, args: Record<string, unknown>): Promise<T> {
      const response = await app.callServerTool({ name, arguments: args });
      const data = response.structuredContent as
        | { status: string; result: T; message?: string; error_code?: string }
        | undefined;
      if (response.isError || !data || data.status !== "ok")
        throw new Error(
          `${data?.error_code ?? "Tool error"}: ${
            data?.message ??
            (response.content
              ?.filter((item) => item.type === "text")
              .map((item) => item.text)
              .join("\n") ||
              "No structured result")
          }`,
        );
      return data.result;
    },
    async continue(sessionId: string, subjects: string[]) {
      if (!extensions.message)
        throw new Error("Host does not support same-conversation continuation");
      const result = await extensions.message.send({
        role: "user",
        content: [
          {
            type: "text",
            text: `Auto-bean import session ${sessionId}: saved review batch is ready. Updated subjects: ${JSON.stringify(subjects)}. Read the current review artifacts and continue this import in the same conversation.`,
          },
        ],
        _meta: { "openai/message": { target: "active", send: true } },
      });
      if (result.isError)
        throw new Error(
          "Host could not deliver the continuation. Your changes remain saved.",
        );
    },
  };
}
