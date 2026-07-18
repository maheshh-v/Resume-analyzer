import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { safeRedirectPath } from "@/lib/utils";

// The candidate interview portal is a tokenized public link (see docs/ARCHITECTURE.md) —
// it must never require a recruiter session. Everything else under the app is recruiter-only.
// /auth/callback MUST stay public: it's hit mid-OAuth, before any session cookie exists —
// bouncing it to /login drags the one-shot ?code= along and kills the PKCE exchange.
// /benchmarks is a public, unauthenticated marketing/technical page — reproducible accuracy
// numbers anyone can see without a recruiter session.
const PUBLIC_PATH_PREFIXES = ["/login", "/auth", "/interview", "/benchmarks", "/_next", "/favicon.ico"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const pathname = request.nextUrl.pathname;

  if (!user && !isPublicPath(pathname)) {
    // Fresh URL, not a clone: cloning would carry the original query string (including a
    // stray one-shot ?code=) onto the login page.
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (user && pathname === "/login") {
    const next = safeRedirectPath(request.nextUrl.searchParams.get("next"));
    return NextResponse.redirect(new URL(next, request.url));
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
