# Website Access Troubleshooting Guide

## Issue Summary

Unable to access: `https://devnetsandbox.cisco.com/DevNet`  
Related issue: Broken CSS on `https://developer.cisco.com/site/sandbox/`

---

## Understanding Your Issue

Based on your symptoms ("Secure Connection Failed" after login), here's what's likely happening:

**Normal login flow:**

1. You visit `devnetsandbox.cisco.com` → redirects to `developer.cisco.com` for login ✅
2. You log in successfully on `developer.cisco.com` ✅
3. Login redirects you back to `devnetsandbox.cisco.com` ❌ **FAILS HERE**

**Why this happens:**

The two domains (`developer.cisco.com` and `devnetsandbox.cisco.com`) are separate:

- `developer.cisco.com` = Login/authentication server (works for you)
- `devnetsandbox.cisco.com` = Sandbox platform (blocked/failing for you)

**Possible causes:**

- ISP blocking `devnetsandbox.cisco.com` specifically (common in some regions)
- Corporate/network firewall blocking the domain
- SSL/TLS certificate issues with `devnetsandbox.cisco.com`
- Man-in-the-middle proxy interfering with SSL
- Outdated browser/OS with incompatible TLS version

**The tests below will help us identify which cause is affecting you.**

---

## Step 1: DNS Resolution Test

First, verify DNS is working correctly:

**Windows:**

```bash
nslookup devnetsandbox.cisco.com > dns-test.txt
nslookup developer.cisco.com >> dns-test.txt
```

**Mac/Linux:**

```bash
nslookup devnetsandbox.cisco.com > dns-test.txt
nslookup developer.cisco.com >> dns-test.txt
```

**What to look for:**

- ✅ You should see IP addresses returned
- ❌ `server can't find` = DNS blocking or resolution failure

---

## Step 2: SSL/TLS Connection Test

Test if SSL/TLS handshake works (this helps identify "Secure Connection Failed" issues):

**All platforms (if openssl is available):**

```bash
# Test devnetsandbox.cisco.com SSL
echo | openssl s_client -connect devnetsandbox.cisco.com:443 -servername devnetsandbox.cisco.com 2>&1 > sandbox-ssl.txt

# Test developer.cisco.com SSL
echo | openssl s_client -connect developer.cisco.com:443 -servername developer.cisco.com 2>&1 > developer-ssl.txt
```

**What to look for in the output files:**

- ✅ `Verify return code: 0 (ok)` = SSL works
- ❌ `Verify return code: 20` or `21` = Certificate chain issue
- ❌ `Connection refused` or `timeout` = Port 443 blocked
- ❌ `handshake failure` = TLS version or cipher mismatch

**Installing openssl** (if needed):

- Windows: Download from [Win32 OpenSSL](https://slproweb.com/products/Win32OpenSSL.html)
- Mac: Pre-installed
- Linux: `sudo apt-get install openssl` or `sudo yum install openssl`

---

## Step 3: curl Tests

Run these commands in your terminal and save the output:

```bash
# Test main site (save output to file)
curl -v -L https://devnetsandbox.cisco.com/DevNet 2>&1 > sandbox-debug.txt

# Test CSS domain
curl -v https://developer.cisco.com/site/sandbox/ 2>&1 > developer-debug.txt

# Test login domain
curl -v https://developer.cisco.com 2>&1 > developer-main.txt
```

**What to look for in the output files:**

- ✅ `HTTP/2 200` or `HTTP/1.1 200` = Success
- ✅ `HTTP/1.1 302` or `301` = Redirect (normal for login flows)
- ❌ `403 Forbidden` or `451 Unavailable` = Site blocked by ISP/firewall
- ❌ `SSL certificate problem` = Certificate/security issue
- ❌ `Could not resolve host` = DNS issue
- ❌ `Connection timed out` = Network/firewall blocking
- ❌ `SSL peer handshake failed` = SSL/TLS blocked or incompatible

**Installing curl** (if needed):

- Windows 10/11: Pre-installed
- Mac: Pre-installed
- Linux: `sudo apt-get install curl` or `sudo yum install curl`

---

## Step 4: Browser Developer Tools

### 4.1 Open Developer Tools

1. Open your browser
2. Press **F12** (or **Ctrl+Shift+I** / **Cmd+Option+I**)
3. **Important:** Go to **Network** tab BEFORE loading the page
4. Check "Preserve log" option (keeps logs during redirects)
5. Try loading: `https://devnetsandbox.cisco.com/DevNet`

### 4.2 What to Check

**Network Tab (Most Important):**

1. Look for failed requests (shown in red)
2. Look at the **entire request chain** (should show multiple requests during SSO login redirect)
3. For each failed request, click it and check:
   - **Status Code** (200 = success, 3xx = redirect, 4xx/5xx = error)
   - **Headers** tab → Response Headers
   - **Timing** tab → Look for "Stalled" or "SSL" delays
4. Screenshot the Network tab showing ALL requests (including redirects)
5. Right-click failed request → **Copy** → **Copy as HAR** (save to file)

**Security Tab (Chrome/Edge):**

1. Switch to **Security** tab
2. Click "View certificate"
3. Screenshot any warnings or errors
4. Check if certificate is valid and trusted

**Console Tab:**

- Switch to **Console** tab
- Look for errors in red (especially SSL/certificate errors)
- Screenshot any errors

**Common error patterns:**

- `Mixed Content` = HTTP resources on HTTPS page
- `CORS policy` = Cross-origin blocking
- `net::ERR_CERT_AUTHORITY_INVALID` = Certificate not trusted
- `net::ERR_CERT_DATE_INVALID` = System clock wrong
- `net::ERR_CERT_COMMON_NAME_INVALID` = Certificate name mismatch
- `net::ERR_CONNECTION_REFUSED` = Port blocked
- `net::ERR_CONNECTION_TIMED_OUT` = Network/firewall blocking
- `net::ERR_SSL_PROTOCOL_ERROR` = SSL/TLS handshake failed
- `SSL_ERROR_NO_CYPHER_OVERLAP` (Firefox) = TLS version incompatible

### 4.3 SSO Redirect Chain Analysis

**What should happen during normal login:**

1. Request to `devnetsandbox.cisco.com` → 302 redirect
2. Redirect to `developer.cisco.com/login` → 200 OK (login page loads)
3. After login → 302 redirect back to `devnetsandbox.cisco.com`
4. Final page load → 200 OK

**If step 3 or 4 fails with "Secure Connection Failed":**

- This suggests `devnetsandbox.cisco.com` SSL/TLS is blocked but `developer.cisco.com` is not
- Screenshot the Network tab showing where the redirect chain breaks

### 4.4 Quick Tests

Try these variations:

- [ ] **Incognito/Private mode** (Ctrl+Shift+N or Cmd+Shift+N) - Does it work?
- [ ] **Different browser** (Chrome, Firefox, Edge) - Does it work?
- [ ] **Disable extensions** (Settings → Extensions → Disable all) - Does it work?
- [ ] **Check system date/time** - Is it correct? (Wrong clock causes SSL errors)
- [ ] **Try on mobile network** (if available via hotspot) - Does it work?

---

## Alternative: Online Testing Tools

**If you cannot install curl or openssl**, use these online tools and screenshot the results:

### SSL/TLS Certificate Check

Visit these sites and test `devnetsandbox.cisco.com`:

- [SSL Labs](https://www.ssllabs.com/ssltest/analyze.html)
- [SSL Shopper](https://www.sslshopper.com/ssl-checker.html)

Screenshot any errors or warnings.

### DNS Check

Visit and test both domains:

- [DNS Checker](https://dnschecker.org)
- Enter `devnetsandbox.cisco.com` and check if it resolves
- Enter `developer.cisco.com` and check if it resolves

Screenshot the results.

### Website Connectivity Check

Visit and test the full URL:

- [Is It Down Right Now](https://www.isitdownrightnow.com)
- Enter `https://devnetsandbox.cisco.com`

Screenshot the result.

---

## Step 5: What to Report

Please share the following diagnostic information:

### Files (from command-line tests)

- `dns-test.txt` (DNS resolution)
- `sandbox-ssl.txt` (SSL/TLS test for devnetsandbox.cisco.com)
- `developer-ssl.txt` (SSL/TLS test for developer.cisco.com)
- `sandbox-debug.txt` (curl test for devnetsandbox)
- `developer-debug.txt` (curl test for developer.cisco.com/site/sandbox)
- `developer-main.txt` (curl test for developer.cisco.com)
- HAR file from browser (if available)

### Screenshots (from browser)

1. **Network tab** showing:
   - Full request chain (including redirects)
   - Failed requests highlighted
   - Headers tab of failed request
   - Timing tab of failed request
2. **Console tab** showing any errors
3. **Security tab** showing certificate status
4. **The actual error page** you see

### Quick Questions

- [ ] Does it work in incognito mode?
- [ ] Does it work in a different browser?
- [ ] Does `https://www.cisco.com` work normally?
- [ ] Is your system date/time correct?
- [ ] Can you try on a different network (e.g., mobile hotspot)?
- [ ] Are you using a VPN, proxy, or corporate network?
- [ ] What country/region are you in?

---

## Common Issues & Solutions

| Symptom                                         | Likely Cause                     | Solution                                            |
| ----------------------------------------------- | -------------------------------- | --------------------------------------------------- |
| DNS test fails for devnetsandbox only           | DNS blocking/hijacking           | Try mobile network or VPN                           |
| openssl shows "connection refused" or "timeout" | Port 443 blocked by ISP/firewall | Try VPN or different network                        |
| openssl shows "handshake failure"               | TLS version incompatible         | Update browser/OS or try different device           |
| openssl shows "Verify return code: 20 or 21"    | Certificate chain issue          | Check system time, update root certificates         |
| curl shows `403 Forbidden` or `451 Unavailable` | ISP/government blocking          | Try VPN or contact network admin                    |
| curl works, browser fails                       | Browser security/extensions      | Try incognito + disable extensions                  |
| Browser shows certificate errors                | System clock wrong or MITM proxy | Check date/time settings, check for corporate proxy |
| Login works but redirect fails                  | Selective domain blocking        | `devnetsandbox.cisco.com` may be blocked - try VPN  |
| CSS loads but appears broken                    | Content Security Policy / CORS   | Check Console for CSP/CORS errors                   |
| Works on mobile network, fails on WiFi          | ISP or network firewall blocking | Contact ISP or network administrator                |

---

**Last Updated:** November 14, 2025
