// Serves the site's static files. Video files go through here first so we can
// answer "Range" requests (part of a file), which Safari and iPhones need to
// play video. Everything else is served straight from /public.
export default {
  async fetch(request, env) {
    const range = request.headers.get('Range');
    const plain = new Request(request.url, { method: request.method, headers: { Accept: request.headers.get('Accept') || '*/*' } });
    const res = await env.ASSETS.fetch(plain);
    const headers = new Headers(res.headers);
    headers.set('Accept-Ranges', 'bytes');
    if (!range || res.status !== 200) return new Response(res.body, { status: res.status, headers });

    const body = await res.arrayBuffer();
    const size = body.byteLength;
    const m = /^bytes=(\d*)-(\d*)$/.exec(range.trim());
    let start, end;
    if (m && m[1] !== '') { start = +m[1]; end = m[2] !== '' ? Math.min(+m[2], size - 1) : size - 1; }
    else if (m && m[2] !== '') { start = Math.max(size - +m[2], 0); end = size - 1; }
    if (start === undefined || start > end || start >= size) {
      headers.set('Content-Range', `bytes */${size}`);
      headers.delete('Content-Length');
      return new Response(null, { status: 416, headers });
    }
    headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
    headers.set('Content-Length', String(end - start + 1));
    return new Response(request.method === 'HEAD' ? null : body.slice(start, end + 1), { status: 206, headers });
  },
};
