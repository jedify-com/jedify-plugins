import {
  protectedResourceHandler,
  metadataCorsOptionsRequestHandler,
} from "mcp-handler";

const handler = protectedResourceHandler({
  authServerUrls: [
    "https://auth.app.jedify.com/v1/apps/P2fGtsAm5ziAZr0swDyMDO7Tce87",
  ],
});

const OPTIONS = metadataCorsOptionsRequestHandler();

export { handler as GET, OPTIONS };
