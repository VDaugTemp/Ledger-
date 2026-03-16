const BACKEND_URL =
  process.env.BACKEND_URL ??
  (process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : "http://localhost:8000");

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const userId = searchParams.get("userId") ?? "";

  const backendRes = await fetch(
    `${BACKEND_URL}/app/chat/threads?user_id=${encodeURIComponent(userId)}`,
  );

  if (!backendRes.ok) {
    return new Response(JSON.stringify({ threads: [] }), {
      status: backendRes.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  const data = await backendRes.json();
  return Response.json(data);
}
