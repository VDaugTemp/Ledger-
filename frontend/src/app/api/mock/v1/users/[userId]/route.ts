import { NextResponse } from "next/server";
import { users, profiles, makeDefaultProfile } from "../../../_store";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  const { userId } = await params;

  let user = users.get(userId);
  if (!user) {
    // Hydrate from client-side store on refresh — create a shell record
    user = { userId, createdAt: new Date().toISOString() };
    users.set(userId, user);
  }

  let profile = profiles.get(userId);
  if (!profile) {
    profile = makeDefaultProfile();
    profiles.set(userId, profile);
  }

  return NextResponse.json({ user, profile });
}
