import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import { authenticatedFetch } from "@/lib/fetch-with-auth";
import { DASHBOARD_API_URL } from "@/lib/api";

const FIVE_MINUTES_MS = 5 * 60 * 1000;

export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  basePath: "/auth/api",
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  callbacks: {
    async signIn({ user }) {
      try {
        await authenticatedFetch(
          `${DASHBOARD_API_URL}/dashboard/auth/upsert-user`,
          {
            method: "POST",
            body: JSON.stringify({
              email: user.email,
              name: user.name,
              image: user.image,
            }),
          },
        );
      } catch (error) {
        console.error("Failed to upsert user:", error);
      }
      return true;
    },

    async jwt({ token, user, trigger }) {
      // On initial sign-in, extract domain and read approval from DB
      if (trigger === "signIn" && user?.email) {
        const domain = user.email.split("@").pop() ?? "";
        token.domain = domain;
        // Read actual approval status from DB instead of deriving from domain
        try {
          const res = await authenticatedFetch(
            `${DASHBOARD_API_URL}/dashboard/auth/check-user?email=${encodeURIComponent(user.email)}`,
          );
          if (res.ok) {
            const data = await res.json();
            token.approved = Boolean(data.approved);
          } else {
            token.approved = domain === "2weeks.co";
          }
        } catch {
          token.approved = domain === "2weeks.co";
        }
        token.approvedCheckedAt = Date.now();
      }

      // Periodically refresh approval status (every 5 minutes)
      const now = Date.now();
      const lastChecked = token.approvedCheckedAt ?? 0;
      if (token.email && now - lastChecked > FIVE_MINUTES_MS) {
        try {
          const res = await authenticatedFetch(
            `${DASHBOARD_API_URL}/dashboard/auth/check-user?email=${encodeURIComponent(token.email as string)}`,
          );
          if (res.ok) {
            const data = await res.json();
            token.approved = Boolean(data.approved);
          }
        } catch (error) {
          console.error("Failed to check user approval:", error);
        }
        token.approvedCheckedAt = now;
      }

      return token;
    },

    async session({ session, token }) {
      session.user.approved = token.approved ?? false;
      session.user.domain = token.domain ?? "";
      return session;
    },
  },
});
