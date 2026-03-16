const BACKEND_URL =
  process.env.BACKEND_URL ??
  (process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : "http://localhost:8000");

export async function POST(req: Request) {
  const { threadId } = (await req.json()) as { threadId: string };

  const res = await fetch(`${BACKEND_URL}/app/chat/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId }),
  });

  if (!res.ok) {
    return Response.json({ error: "Backend error" }, { status: res.status });
  }

  return Response.json(await res.json());
}
