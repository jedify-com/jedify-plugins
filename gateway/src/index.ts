export default {
  async fetch(): Promise<Response> {
    return new Response("jedify-gateway: not yet wired", { status: 200 });
  },
};
