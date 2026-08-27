"use strict";

// Interface availability for every participant domain.
//
// This suite exists because a reachable endpoint is not evidence of a working
// flow. On 2026-08-18 both participant domains answered on port 443 with a
// valid certificate and the correct virtual host, and still served nothing but
// the default nginx 404 body: TLS was healthy, Keycloak was healthy, and the
// site was down. Nothing in the pipeline noticed, because nothing in the
// pipeline looked at what the browser actually rendered.
//
// Every assertion below therefore inspects the rendered document. None of them
// accepts a status code as proof.

const { test, expect } = require("@playwright/test");
const { selectedProfiles } = require("./domains");

// A server-generated error body — nginx, Apache or a gateway — never contains
// the participant shell. Matching the title is enough to tell "the origin
// answered" from "the origin served the application".
const SERVER_ERROR_TITLE = /^(\d{3})\s|\b(404 Not Found|502 Bad Gateway|503 Service Unavailable)\b/i;

for (const profile of selectedProfiles()) {
  test.describe(`participant interface · ${profile.id}`, () => {
    test.use({ baseURL: profile.baseUrl });

    test("the site root renders the participant shell, not a server error page", async ({ page }) => {
      const response = await page.goto("/", { waitUntil: "domcontentloaded" });
      expect(response, `${profile.baseUrl} produced no response`).not.toBeNull();

      // Read the document before asserting on status, so a failure reports what
      // was actually served instead of only a number.
      const title = (await page.title()).trim();
      expect(
        title,
        `${profile.baseUrl} served a server error page titled "${title}" ` +
          `(HTTP ${response.status()}). The origin is reachable but the site is not being served.`
      ).not.toMatch(SERVER_ERROR_TITLE);

      expect(response.ok(), `${profile.baseUrl} returned HTTP ${response.status()}`).toBe(true);

      // The shell must be a real document with rendered content, not an empty
      // body that happens to return 200.
      await expect(page.locator("body")).not.toBeEmpty();
      const text = (await page.locator("body").innerText()).trim();
      expect(text.length, `${profile.baseUrl} rendered an empty body`).toBeGreaterThan(0);
    });

    test("the shell identifies the domain it belongs to", async ({ page }) => {
      await page.goto("/", { waitUntil: "domcontentloaded" });

      // Guards against a domain being served another domain's build, which a
      // status check cannot see at all.
      await expect(
        page.locator("body"),
        `${profile.baseUrl} does not present the ${profile.brand} brand`
      ).toContainText(new RegExp(profile.brand.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"));
    });

    test("the login entry point reaches the federated identity provider", async ({ page }) => {
      await page.goto("/login.html", { waitUntil: "domcontentloaded" });

      const federatedLogin = page.getByRole("button", {
        name: /identidad federada|federated identity/i
      });
      await expect(
        federatedLogin,
        `${profile.baseUrl}/login.html does not offer a federated identity entry point`
      ).toBeVisible();

      await federatedLogin.click();

      // A real navigation to the identity provider, with its form rendered.
      // This is the point where a broken realm, a wrong KC_HOSTNAME or a stale
      // client redirect stops being invisible.
      await page.waitForURL(url => url.href.startsWith(profile.authBaseUrl), { timeout: 20_000 });
      await expect(
        page.locator("#username"),
        `${profile.authBaseUrl} did not render a credential form`
      ).toBeVisible();
    });
  });
}
