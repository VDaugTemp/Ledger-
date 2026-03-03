import {
  CognitoIdentityProviderClient,
  SignUpCommand,
  ConfirmSignUpCommand,
  InitiateAuthCommand,
  type AuthenticationResultType,
} from "@aws-sdk/client-cognito-identity-provider";

const REGION = process.env.NEXT_PUBLIC_COGNITO_REGION ?? "eu-west-2";
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "";
console.log("Cognito config:", { REGION, CLIENT_ID });
const cognitoClient = new CognitoIdentityProviderClient({ region: REGION });

export type CognitoTokens = {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresIn: number;
};

export type JwtPayload = {
  sub: string;
  email?: string;
  [key: string]: unknown;
};

/** Decode JWT payload without verifying signature (browser-safe, uses atob). */
export function decodeJwtPayload(jwt: string): JwtPayload {
  const [, payload] = jwt.split(".");
  const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(base64);
  return JSON.parse(json) as JwtPayload;
}

function extractTokens(auth: AuthenticationResultType): CognitoTokens {
  if (!auth.AccessToken || !auth.IdToken || !auth.RefreshToken) {
    throw new Error("Incomplete tokens from Cognito");
  }
  return {
    accessToken: auth.AccessToken,
    idToken: auth.IdToken,
    refreshToken: auth.RefreshToken,
    expiresIn: auth.ExpiresIn ?? 3600,
  };
}

/** Map Cognito error names to user-friendly messages. */
export function cognitoErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "name" in error) {
    const name = (error as { name: string }).name;
    const map: Record<string, string> = {
      UsernameExistsException: "An account with this email already exists.",
      UserNotFoundException: "No account found with this email.",
      NotAuthorizedException: "Incorrect email or password.",
      CodeMismatchException: "Verification code is incorrect.",
      ExpiredCodeException: "Verification code has expired. Please request a new one.",
      UserNotConfirmedException: "Please verify your email before signing in.",
      InvalidPasswordException:
        "Password does not meet requirements (min 8 chars, upper, lower, number).",
      LimitExceededException: "Too many attempts. Please wait a moment and try again.",
    };
    return (
      map[name] ??
      (process.env.NODE_ENV === "development"
        ? name
        : "An error occurred. Please try again.")
    );
  }
  return "An unexpected error occurred.";
}

export async function signUp(email: string, password: string): Promise<void> {
  await cognitoClient.send(
    new SignUpCommand({ ClientId: CLIENT_ID, Username: email, Password: password }),
  );
}

export async function confirmSignUp(email: string, code: string): Promise<void> {
  await cognitoClient.send(
    new ConfirmSignUpCommand({
      ClientId: CLIENT_ID,
      Username: email,
      ConfirmationCode: code,
    }),
  );
}

export async function signIn(email: string, password: string): Promise<CognitoTokens> {
  const res = await cognitoClient.send(
    new InitiateAuthCommand({
      ClientId: CLIENT_ID,
      AuthFlow: "USER_PASSWORD_AUTH",
      AuthParameters: { USERNAME: email, PASSWORD: password },
    }),
  );
  if (res.ChallengeName) throw new Error(`Unexpected challenge: ${res.ChallengeName}`);
  if (!res.AuthenticationResult) throw new Error("Missing AuthenticationResult");
  return extractTokens(res.AuthenticationResult);
}

/**
 * Refresh using stored refresh token.
 * Note: Cognito does NOT return a new refresh token on refresh — keep the old one.
 */
export async function refreshSession(
  refreshToken: string,
): Promise<Omit<CognitoTokens, "refreshToken">> {
  const res = await cognitoClient.send(
    new InitiateAuthCommand({
      ClientId: CLIENT_ID,
      AuthFlow: "REFRESH_TOKEN_AUTH",
      AuthParameters: { REFRESH_TOKEN: refreshToken },
    }),
  );
  if (!res.AuthenticationResult) throw new Error("Missing AuthenticationResult on refresh");
  const auth = res.AuthenticationResult;
  if (!auth.AccessToken || !auth.IdToken) throw new Error("Missing tokens on refresh");
  return {
    accessToken: auth.AccessToken,
    idToken: auth.IdToken,
    expiresIn: auth.ExpiresIn ?? 3600,
  };
}
