import { NextResponse } from "next/server";
import { nanoid } from "nanoid";
import { users, profiles, makeDefaultProfile } from "../../_store";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const userId = nanoid();
  const createdAt = new Date().toISOString();

  users.set(userId, { userId, email: body.email, createdAt });
  profiles.set(userId, makeDefaultProfile());

  return NextResponse.json({ userId }, { status: 201 });
}
