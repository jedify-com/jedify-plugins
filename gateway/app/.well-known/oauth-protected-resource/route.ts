import {
  protectedResourceHandler,
  metadataCorsOptionsRequestHandler,
} from "mcp-handler";

const handler = protectedResourceHandler({
  authServerUrls: [
    "https://api.descope.com/v1/apps/P3EwuWB0eAPKe8h4vvQ2QhinomOE",
  ],
});

const OPTIONS = metadataCorsOptionsRequestHandler();

export { handler as GET, OPTIONS };
