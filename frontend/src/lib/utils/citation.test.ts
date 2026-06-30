import { describe, expect, it } from "vitest";
import { buildCitationItems } from "./citation";

describe("buildCitationItems", () => {
  it("parses [n] citations and replaces existing t query param", () => {
    const items = buildCitationItems("Noi dung [0] va [1]", {
      video_url: ["https://youtube.com/watch?v=a", "https://youtu.be/b?t=2"],
      title: ["Video A", "Video B"],
      filename: ["a.txt", "b.txt"],
      start_timestamp: ["00:01:05", "00:00:10"],
      end_timestamp: ["00:01:20", "00:00:20"],
      confidence: ["high", "low"],
    });

    expect(items).toEqual([
      {
        index: 0,
        marker: "[0]",
        title: "Video A",
        filename: "a.txt",
        start_timestamp: "00:01:05",
        end_timestamp: "00:01:20",
        confidence: "high",
        video_url: "https://youtube.com/watch?v=a&t=65",
      },
      {
        index: 1,
        marker: "[1]",
        title: "Video B",
        filename: "b.txt",
        start_timestamp: "00:00:10",
        end_timestamp: "00:00:20",
        confidence: "low",
        video_url: "https://youtu.be/b?t=10",
      },
    ]);
  });

  it("appends t query param for URL without existing query", () => {
    const items = buildCitationItems("Noi dung [0]", {
      video_url: ["https://youtu.be/b"],
      title: ["Video B"],
      filename: ["b.txt"],
      start_timestamp: ["00:00:10"],
      end_timestamp: ["00:00:20"],
      confidence: ["low"],
    });

    expect(items).toEqual([
      {
        index: 0,
        marker: "[0]",
        title: "Video B",
        filename: "b.txt",
        start_timestamp: "00:00:10",
        end_timestamp: "00:00:20",
        confidence: "low",
        video_url: "https://youtu.be/b?t=10",
      },
    ]);
  });

  it("returns out_of_range warning when citation has no video", () => {
    const items = buildCitationItems("Chi co [2]", {
      video_url: ["https://youtube.com/watch?v=a"],
      title: ["Video A"],
      filename: ["a.txt"],
      start_timestamp: ["00:00:05"],
      end_timestamp: ["00:00:10"],
      confidence: ["medium"],
    });

    expect(items).toEqual([
      {
        index: 2,
        marker: "[2]",
        title: "",
        filename: "",
        start_timestamp: "",
        end_timestamp: "",
        confidence: "",
        video_url: "",
        warning: "out_of_range",
      },
    ]);
  });

  it("rejects citation URL with unsafe protocol", () => {
    const items = buildCitationItems("Noi dung [0]", {
      video_url: ["javascript:alert(1)"],
      title: ["Unsafe"],
      filename: ["unsafe.txt"],
      start_timestamp: ["00:00:03"],
      end_timestamp: ["00:00:05"],
      confidence: ["low"],
    });

    expect(items).toEqual([
      {
        index: 0,
        marker: "[0]",
        title: "Unsafe",
        filename: "unsafe.txt",
        start_timestamp: "00:00:03",
        end_timestamp: "00:00:05",
        confidence: "low",
        video_url: "",
        warning: "unsafe_url",
      },
    ]);
  });
});
