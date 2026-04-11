import { auth } from "@/lib/auth";

const publicPaths = ["/", "/demo"];

function isPublicPath(pathname: string): boolean {
  if (publicPaths.includes(pathname)) return true;
  if (pathname.startsWith("/auth/")) return true;
  if (pathname.startsWith("/_next/")) return true;
  if (pathname === "/favicon.ico") return true;
  // Static assets (files with extensions like .js, .css, .png)
  if (/\.\w+$/.test(pathname)) return true;
  return false;
}

export default auth((req) => {
  const { pathname } = req.nextUrl;

  if (isPublicPath(pathname)) return;

  const session = req.auth;

  // Not logged in — redirect to sign-in
  if (!session?.user) {
    const signInUrl = new URL("/auth/signin", req.url);
    signInUrl.searchParams.set("callbackUrl", pathname);
    return Response.redirect(signInUrl);
  }

  // Logged in but NOT approved — redirect to pending page
  if (!session.user.approved && pathname !== "/auth/pending") {
    return Response.redirect(new URL("/auth/pending", req.url));
  }

  // Approved user on /auth/pending — redirect to dashboard
  if (session.user.approved && pathname === "/auth/pending") {
    return Response.redirect(new URL("/dashboard", req.url));
  }
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.).*)"],
};
