import { getUser } from "@/lib/userApi";

export async function getPostLoginRoute(
  userId: string,
  accessToken: string,
): Promise<"/intake" | "/"> {
  try {
    const { profile } = await getUser(userId, accessToken);
    return profile.dataQuality.intakeCompleted ? "/" : "/intake";
  } catch (err) {
    // 404 = no profile yet → intake
    if (err instanceof Error && err.message.includes("404")) return "/intake";
    return "/intake"; // safe default
  }
}
