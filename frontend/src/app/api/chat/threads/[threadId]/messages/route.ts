const BACKEND_URL =
  process.env.BACKEND_URL ??
  (process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : "http://localhost:8000");

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ threadId: string }> },
) {
  const { threadId } = await params;

  const backendRes = await fetch(
    `${BACKEND_URL}/app/chat/threads/${encodeURIComponent(threadId)}/messages`,
  );

  if (backendRes.status === 404) {
    return new Response(JSON.stringify({ error: "Thread not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!backendRes.ok) {
    return new Response(JSON.stringify({ error: "Backend error" }), {
      status: backendRes.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  const data = await backendRes.json();
  return Response.json(data);
}
