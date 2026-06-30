import { timestampToSeconds } from "./timestamp";

export function buildCitationItemsFromContext(text: string, docs: any[]): CitationItem[] {
  const matches = [...text.matchAll(/\[(\d+)\]/g)];
  
  // Deduplicate by index
  const uniqueIndices = new Set<number>();
  const uniqueMatches: { index: number, marker: string }[] = [];
  
  for (const match of matches) {
    const index = Number(match[1]);
    if (!uniqueIndices.has(index)) {
      uniqueIndices.add(index);
      uniqueMatches.push({ index, marker: match[0] });
    }
  }

  return uniqueMatches.map(({ index, marker }) => {
    const doc = docs[index];
    if (!doc) {
      return {
        index,
        marker,
        title: "Nguồn không xác định",
        filename: "",
        start_timestamp: "",
        end_timestamp: "",
        confidence: "low",
        video_url: "",
        warning: "out_of_range" as const,
      };
    }
    
    const rawVideoUrl = doc.video_url || "";
    const safeVideoUrl = sanitizeCitationUrl(rawVideoUrl);
    const startTimestamp = doc.start || doc.start_timestamp || "";
    const seconds = timestampToSeconds(startTimestamp);
    
    let finalUrl = safeVideoUrl;
    if (safeVideoUrl && seconds > 0) {
      try {
        const urlObj = new URL(safeVideoUrl);
        urlObj.searchParams.set("t", String(seconds));
        finalUrl = urlObj.toString();
      } catch (e) {
        console.error("Error building citation URL:", e);
      }
    }

    return {
      index,
      marker,
      title: doc.title || "Video bài giảng",
      filename: doc.filename || "",
      start_timestamp: startTimestamp,
      end_timestamp: doc.end || doc.end_timestamp || "",
      confidence: "medium",
      video_url: finalUrl,
      ...(!rawVideoUrl ? { warning: "out_of_range" as const } : !safeVideoUrl ? { warning: "unsafe_url" as const } : {}),
    };
  });

}

type CitationMetadata = {
  video_url: string[];
  title: string[];
  filename: string[];
  start_timestamp: string[];
  end_timestamp: string[];
  confidence: string[];
};

export type CitationItem = {
  index: number;
  marker: string;
  title: string;
  filename: string;
  start_timestamp: string;
  end_timestamp: string;
  confidence: string;
  video_url: string;
  warning?: "out_of_range" | "unsafe_url";
};

function sanitizeCitationUrl(videoUrl: string): string {
  if (!videoUrl) return "";
  let urlStr = videoUrl.trim();
  
  // Handle protocol-relative or missing protocol
  if (urlStr.startsWith("//")) {
    urlStr = "https:" + urlStr;
  } else if (!urlStr.match(/^[a-zA-Z]+:\/\//)) {
    urlStr = "https://" + urlStr;
  }

  try {
    const url = new URL(urlStr);
    // Basic YouTube domain validation if needed, but keep it generic for now
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return "";
    }
    return url.toString();
  } catch {
    return "";
  }
}

export function buildCitationItems(text: string, metadata: CitationMetadata): CitationItem[] {
  const matches = [...text.matchAll(/\[(\d+)\]/g)];

  // Deduplicate by index
  const uniqueIndices = new Set<number>();
  const uniqueMatches: { index: number, marker: string }[] = [];
  
  for (const match of matches) {
    const index = Number(match[1]);
    if (!uniqueIndices.has(index)) {
      uniqueIndices.add(index);
      uniqueMatches.push({ index, marker: match[0] });
    }
  }

  return uniqueMatches.map(({ index, marker }) => {
    const rawVideoUrl = metadata.video_url[index] ?? "";
    const safeVideoUrl = sanitizeCitationUrl(rawVideoUrl);
    const startTimestamp = metadata.start_timestamp[index] ?? "";
    const seconds = timestampToSeconds(startTimestamp);

    let finalUrl = safeVideoUrl;
    if (safeVideoUrl && seconds > 0) {
      try {
        const urlObj = new URL(safeVideoUrl);
        urlObj.searchParams.set("t", String(seconds));
        finalUrl = urlObj.toString();
      } catch (e) {
        console.error("Error building citation URL:", e);
      }
    }

    return {
      index,
      marker,
      title: metadata.title[index] ?? "Video bài giảng",
      filename: metadata.filename[index] ?? "",
      start_timestamp: startTimestamp,
      end_timestamp: metadata.end_timestamp[index] ?? "",
      confidence: metadata.confidence[index] ?? "medium",
      video_url: finalUrl,
      ...(!rawVideoUrl ? { warning: "out_of_range" as const } : !safeVideoUrl ? { warning: "unsafe_url" as const } : {}),
    };
  });

}
