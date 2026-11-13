// Private Xtream Codes-compatible playlist gateway for OpenIPTV.
// Deploy as a Cloudflare Worker; never expose GitHub or gateway secrets in source.
const OWNER = "mfgs-git";
const REPO = "IPTV-Streams";
const PATH = "playlists/sports.m3u";
const enc = encodeURIComponent;
function auth(url, env) {
  const u = url.searchParams.get("username") || "";
  const p = url.searchParams.get("password") || "";
  return Boolean(env.XTREAM_USERNAME && env.XTREAM_PASSWORD && u === env.XTREAM_USERNAME && p === env.XTREAM_PASSWORD);
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {status, headers: {"content-type":"application/json; charset=utf-8", "cache-control":"no-store"}});
}
function err(status=401) {return json({error:status===401?"Invalid credentials":"Not found"},status);}
function idFor(s) {let h=2166136261; for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return (h>>>0).toString();}
function parseM3U(text) {
  const items=[];let meta=null;
  for(const line0 of text.split(/\r?\n/)) {
    const line=line0.trim();
    if(line.startsWith("#EXTINF:")) meta=line;
    else if(line && !line.startsWith("#")) {
      if(meta && /^https?:\/\//i.test(line) && !/\.m3u(?:\?|$)/i.test(line)) {
        const name=(meta.split(",").slice(1).join(",")||"Channel").trim();
        const group=(meta.match(/group-title="([^"]*)"/)||[])[1]||"Other";
        const logo=(meta.match(/tvg-logo="([^"]*)"/)||[])[1]||"";
        items.push({id:idFor(line),url:line,name,group,logo});
      }
      meta=null;
    }
  }
  return items;
}
async function channels(env) {
  const api=`https://api.github.com/repos/${OWNER}/${REPO}/contents/${PATH}`;
  const res=await fetch(api,{headers:{
    "Authorization":`Bearer ${env.GITHUB_TOKEN}`,
    "Accept":"application/vnd.github.raw+json",
    "User-Agent":"private-iptv-gateway",
    "X-GitHub-Api-Version":"2022-11-28"
  },cf:{cacheTtl:120,cacheEverything:true}});
  if(!res.ok) throw new Error("GitHub playlist fetch failed: "+res.status);
  const raw=await res.text();
  // GitHub raw content negotiation should return text, not JSON.
  if(!raw.startsWith("#EXTM3U")) throw new Error("Playlist is not valid M3U");
  return parseM3U(raw);
}
export default {
  async fetch(request,env) {
    const url=new URL(request.url);
    const path=url.pathname;
    if(path==="/health") return json({status:"ready",service:"private-iptv-gateway"});
    if(!env.GITHUB_TOKEN || !env.XTREAM_USERNAME || !env.XTREAM_PASSWORD) return json({error:"Server secrets are not configured"},503);
    let permitted=auth(url,env);
    const streamMatch=path.match(/^\/live\/([^/]+)\/([^/]+)\/(\d+)(?:\.[a-z0-9]+)?$/i);
    if(streamMatch) permitted=streamMatch[1]===env.XTREAM_USERNAME && streamMatch[2]===env.XTREAM_PASSWORD;
    if(!permitted) return err();
    if(!["/player_api.php","/get.php"].includes(path) && !streamMatch) return err(404);
    try {
      const list=await channels(env);
      if(streamMatch) {
        const item=list.find(x=>x.id===streamMatch[3]);
        if(!item) return err(404);
        // Redirect to the source. The original stream host must permit the client.
        return Response.redirect(item.url,302);
      }
      if(path==="/get.php") {
        const base=url.origin;
        const playlist=["#EXTM3U"];
        for(const item of list) {
          const link=`${base}/live/${enc(env.XTREAM_USERNAME)}/${enc(env.XTREAM_PASSWORD)}/${item.id}.m3u8`;
          playlist.push(`#EXTINF:-1 tvg-logo="${item.logo.replace(/"/g,"")}" group-title="${item.group.replace(/"/g,"")}",${item.name}`,link);
        }
        return new Response(playlist.join("\n")+"\n",{headers:{"content-type":"application/x-mpegURL; charset=utf-8","cache-control":"no-store"}});
      }
      const action=url.searchParams.get("action")||"";
      const groups=[...new Set(list.map(x=>x.group))];
      const categoryId=g=>String(groups.indexOf(g)+1);
      if(action==="get_live_categories") return json(groups.map(g=>({category_id:categoryId(g),category_name:g,parent_id:0})));
      if(action==="get_live_streams") {
        const category=url.searchParams.get("category_id");
        return json(list.filter(x=>!category || categoryId(x.group)===category).map((x,i)=>({
          num:i+1,name:x.name,stream_type:"live",stream_id:Number(x.id),stream_icon:x.logo,
          epg_channel_id:null,added:"0",category_id:categoryId(x.group),
          custom_sid:"",tv_archive:0,direct_source:""
        })));
      }
      if(action==="get_short_epg" || action==="get_simple_data_table") return json({epg_listings:[]});
      if(action==="get_vod_categories" || action==="get_series_categories" || action==="get_vod_streams" || action==="get_series") return json([]);
      return json({
        user_info:{username:env.XTREAM_USERNAME,password:env.XTREAM_PASSWORD,message:"",auth:1,status:"Active",exp_date:null,is_trial:"0",active_cons:"0",created_at:"0",max_connections:"2",allowed_output_formats:["m3u8","ts"]},
        server_info:{url:url.hostname,port:"443",https_port:"443",server_protocol:"https",rtmp_port:"0",timezone:"America/New_York",timestamp_now:Math.floor(Date.now()/1000),time_now:new Date().toISOString()}
      });
    } catch(e) {
      return json({error:"Playlist unavailable; check GitHub token, playlist refresh and Worker logs"},502);
    }
  }
};
