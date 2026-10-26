// Serves dist/ (the static assets) for alexisandthetrexes.com.
// - www.alexisandthetrexes.com redirects to the bare domain.
// - On the temporary *.workers.dev address every response carries X-Robots-Tag: noindex, so search engines
//   only ever index the real domain.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === 'www.alexisandthetrexes.com') {
      url.hostname = 'alexisandthetrexes.com';
      return Response.redirect(url.toString(), 301);
    }
    const res = await env.ASSETS.fetch(request);
    if (!url.hostname.endsWith('.workers.dev')) return res;
    const out = new Response(res.body, res);
    out.headers.set('X-Robots-Tag', 'noindex, nofollow');
    return out;
  },
};
