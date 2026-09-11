/** Reads the `exp` claim (seconds since epoch) from a JWT without verifying its
 * signature — used only to schedule a client-side silent refresh, never for
 * trusting the token's contents. */
export function getJwtExpiryMs(token: string): number | null {
  try {
    const [, payloadB64] = token.split(".");
    const payload = JSON.parse(atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof payload.exp === "number") {
      return payload.exp * 1000;
    }
    return null;
  } catch {
    return null;
  }
}
