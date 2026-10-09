import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const account = {
  id: 41,
  name: "Fictional Test User",
  email: "fictional@example.com",
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body === null ? "" : JSON.stringify(body),
  };
}

function installApiMock({ expireDashboardSession = false } = {}) {
  const calls = [];
  vi.stubGlobal("fetch", vi.fn(async (input, options = {}) => {
    const path = new URL(input).pathname;
    calls.push({ path, options });

    if (path === "/api/auth/me") {
      return jsonResponse({ detail: "Authentication required." }, 401);
    }
    if (path === "/api/auth/register" || path === "/api/auth/login") {
      return jsonResponse({ user: account }, path.endsWith("/register") ? 201 : 200);
    }
    if (path === "/api/auth/logout") return jsonResponse(null, 204);

    if (expireDashboardSession && path.startsWith("/api/health-profile/")) {
      return jsonResponse({ detail: "Authentication required." }, 401);
    }
    if (path.startsWith("/api/health-profile/")) return jsonResponse({ user_id: account.id });
    if (path.startsWith("/api/medical-documents/")
      || path.startsWith("/api/lab-results/")
      || path.startsWith("/api/medicines/")
      || path.startsWith("/api/timeline/")) {
      return jsonResponse({ items: [] });
    }
    return jsonResponse({});
  }));
  return calls;
}

describe("account access", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("registers, loads the signed-in dashboard, logs out, and signs in", async () => {
    const user = userEvent.setup();
    const calls = installApiMock();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "New here? Create an account" }));
    await user.type(screen.getByLabelText(/Full name/), account.name);
    await user.type(screen.getByLabelText("Phone (optional)"), "555-0100");
    await user.type(screen.getByLabelText("Email"), account.email);
    await user.type(screen.getByLabelText(/Password/), "fictional-password-123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(account.name)).toBeInTheDocument();
    await waitFor(() => expect(calls.some((call) => call.path === "/api/health-profile/41")).toBe(true));
    expect(calls.find((call) => call.path === "/api/auth/register").options.credentials).toBe("include");
    expect(calls.filter((call) => call.path.startsWith("/api/")).every(
      (call) => call.options.credentials === "include",
    )).toBe(true);

    await user.click(screen.getAllByRole("button", { name: "Log out" })[0]);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Full name/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(calls.some((call) => call.path === "/api/auth/logout")).toBe(true);

    await user.type(screen.getByLabelText("Email"), account.email);
    await user.type(screen.getByLabelText("Password"), "fictional-password-123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText(account.name)).toBeInTheDocument();
    expect(calls.some((call) => call.path === "/api/auth/login")).toBe(true);
  });

  it("returns to sign-in when a private request reports an expired session", async () => {
    const user = userEvent.setup();
    const calls = installApiMock({ expireDashboardSession: true });
    render(<App />);

    await user.type(await screen.findByLabelText("Email"), account.email);
    await user.type(screen.getByLabelText("Password"), "fictional-password-123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText(account.name)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Full name/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(calls.some((call) => call.path === "/api/health-profile/41")).toBe(true);
  });

  it("shows the temporary clinician-summary notice without calling its API", async () => {
    const user = userEvent.setup();
    const calls = installApiMock();
    render(<App />);

    await user.type(await screen.findByLabelText("Email"), account.email);
    await user.type(screen.getByLabelText("Password"), "fictional-password-123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText(account.name);
    await user.click(screen.getByRole("button", { name: "Doctor Visits" }));
    await user.click(await screen.findByRole("button", { name: "Prepare clinician summary" }));

    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("Update Coming Soon");
    expect(notice).toHaveTextContent("Clinician summaries will be available in a future update.");
    expect(calls.some((call) => call.path === "/api/doctor-visits/summary")).toBe(false);
  });
});
