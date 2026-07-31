import { ExternalLink, Star, TrendingUp, ThumbsUp } from "lucide-react";
import type { Professor } from "../api";

interface Props {
  professor: Professor;
  onClick: () => void;
}

function ratingColor(rating: number | null): string {
  if (rating === null || rating === 0) return "bg-gray-200 text-gray-600";
  if (rating >= 4) return "bg-green-100 text-green-800";
  if (rating >= 3) return "bg-yellow-100 text-yellow-800";
  if (rating >= 2) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

function difficultyColor(diff: number | null): string {
  if (diff === null || diff === 0) return "bg-gray-200 text-gray-600";
  if (diff <= 2) return "bg-green-100 text-green-800";
  if (diff <= 3) return "bg-yellow-100 text-yellow-800";
  if (diff <= 4) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

export default function ProfessorCard({ professor, onClick }: Props) {
  const wta = professor.would_take_again_percent;
  const wtaDisplay =
    wta !== null && wta !== undefined && wta >= 0
      ? `${Math.round(wta)}%`
      : "N/A";

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {professor.first_name} {professor.last_name}
            </h3>
            {professor.rmp_link && (
              <a
                href={professor.rmp_link}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex-shrink-0 text-gray-400 hover:text-indigo-600"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
          <p className="text-xs text-gray-500 truncate">
            {professor.department || "Unknown Department"}
          </p>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Rating badge */}
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-bold px-2 py-1 rounded-md ${ratingColor(professor.avg_rating)}`}
          >
            <Star className="w-3 h-3" />
            {professor.avg_rating?.toFixed(1) ?? "N/A"}
          </span>

          {/* Difficulty badge */}
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-bold px-2 py-1 rounded-md ${difficultyColor(professor.avg_difficulty)}`}
          >
            <TrendingUp className="w-3 h-3" />
            {professor.avg_difficulty?.toFixed(1) ?? "N/A"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
        <span className="flex items-center gap-0.5">
          <ThumbsUp className="w-3 h-3" />
          {wtaDisplay} would take again
        </span>
        <span>{professor.num_ratings} review{professor.num_ratings !== 1 ? "s" : ""}</span>
      </div>

      {professor.tags && professor.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {professor.tags.slice(0, 4).map((tag) => (
            <span
              key={tag.tagName}
              className="text-[10px] px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded-full"
            >
              {tag.tagName}
            </span>
          ))}
          {professor.tags.length > 4 && (
            <span className="text-[10px] px-1.5 py-0.5 text-gray-400">
              +{professor.tags.length - 4} more
            </span>
          )}
        </div>
      )}
    </button>
  );
}
