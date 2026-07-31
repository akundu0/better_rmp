import { useState, useEffect } from "react";
import {
  ArrowLeft,
  Star,
  TrendingUp,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  Loader2,
  BookOpen,
  Calendar,
} from "lucide-react";
import { getProfessorDetail } from "../api";
import type { ProfessorDetail as ProfDetail, Rating } from "../api";

interface Props {
  professorId: string;
  onBack: () => void;
}

function ratingColor(rating: number | null): string {
  if (rating === null || rating === 0) return "bg-gray-200 text-gray-600";
  if (rating >= 4) return "bg-green-500 text-white";
  if (rating >= 3) return "bg-yellow-500 text-white";
  if (rating >= 2) return "bg-orange-500 text-white";
  return "bg-red-500 text-white";
}

function RatingBadge({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="text-center">
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      <div className="flex items-center justify-center gap-0.5 text-sm font-bold text-gray-900">
        <Icon className="w-3.5 h-3.5" />
        {value}
      </div>
    </div>
  );
}

function ReviewCard({ rating }: { rating: Rating }) {
  const date = rating.date
    ? new Date(rating.date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
      })
    : null;

  return (
    <div className="border border-gray-100 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {rating.course && (
            <span className="text-xs font-medium bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full flex items-center gap-0.5">
              <BookOpen className="w-3 h-3" />
              {rating.course}
            </span>
          )}
          {rating.grade && (
            <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
              Grade: {rating.grade}
            </span>
          )}
        </div>
        {date && (
          <span className="text-xs text-gray-400 flex items-center gap-0.5">
            <Calendar className="w-3 h-3" />
            {date}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 text-xs">
        <span className="flex items-center gap-0.5">
          <Star className="w-3 h-3 text-yellow-500" />
          Quality: {rating.clarity_rating ?? "N/A"}
        </span>
        <span className="flex items-center gap-0.5">
          <TrendingUp className="w-3 h-3 text-orange-500" />
          Difficulty: {rating.difficulty_rating ?? "N/A"}
        </span>
        {rating.would_take_again !== null && rating.would_take_again !== undefined && (
          <span className="flex items-center gap-0.5">
            {rating.would_take_again === 1 ? (
              <ThumbsUp className="w-3 h-3 text-green-500" />
            ) : (
              <ThumbsDown className="w-3 h-3 text-red-500" />
            )}
            {rating.would_take_again === 1 ? "Yes" : "No"}
          </span>
        )}
      </div>

      {rating.comment && (
        <p className="text-xs text-gray-700 leading-relaxed">{rating.comment}</p>
      )}

      {rating.rating_tags && (
        <div className="flex flex-wrap gap-1">
          {rating.rating_tags.split("--").filter(Boolean).map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-1.5 py-0.5 bg-gray-50 text-gray-500 rounded-full border border-gray-100"
            >
              {tag.trim()}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3 text-[10px] text-gray-400">
        <span className="flex items-center gap-0.5">
          <ThumbsUp className="w-2.5 h-2.5" /> {rating.thumbs_up}
        </span>
        <span className="flex items-center gap-0.5">
          <ThumbsDown className="w-2.5 h-2.5" /> {rating.thumbs_down}
        </span>
      </div>
    </div>
  );
}

export default function ProfessorDetailView({ professorId, onBack }: Props) {
  const [detail, setDetail] = useState<ProfDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getProfessorDetail(professorId)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [professorId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-4">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-indigo-600 mb-3">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error || "Professor not found"}
        </div>
      </div>
    );
  }

  const wta = detail.would_take_again_percent;
  const wtaDisplay = wta !== null && wta !== undefined && wta >= 0 ? `${Math.round(wta)}%` : "N/A";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 z-10">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-indigo-600 mb-2">
          <ArrowLeft className="w-4 h-4" /> Back to results
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              {detail.first_name} {detail.last_name}
            </h2>
            <p className="text-xs text-gray-500">
              {detail.department || "Unknown Department"}
              {detail.school_name && ` · ${detail.school_name}`}
            </p>
          </div>
          {detail.rmp_link && (
            <a
              href={detail.rmp_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 mt-1"
            >
              RMP <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>

        {/* Stats row */}
        <div className="flex items-center justify-between mt-3 px-2">
          <div className="text-center">
            <div
              className={`inline-flex items-center gap-1 text-lg font-bold px-3 py-1 rounded-lg ${ratingColor(detail.avg_rating)}`}
            >
              {detail.avg_rating?.toFixed(1) ?? "N/A"}
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5">Quality</div>
          </div>
          <RatingBadge label="Difficulty" value={detail.avg_difficulty?.toFixed(1) ?? "N/A"} icon={TrendingUp} />
          <RatingBadge label="Take Again" value={wtaDisplay} icon={ThumbsUp} />
          <RatingBadge label="Reviews" value={String(detail.num_ratings)} icon={Star} />
        </div>

        {/* Tags */}
        {detail.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {detail.tags.map((tag) => (
              <span
                key={tag.tagName}
                className="text-[10px] px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-medium"
              >
                {tag.tagName} ({tag.tagCount})
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Ratings list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Recent Reviews ({detail.ratings.length})
        </h3>
        {detail.ratings.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No reviews yet</p>
        ) : (
          detail.ratings.map((rating, i) => (
            <ReviewCard key={rating.id || i} rating={rating} />
          ))
        )}
      </div>
    </div>
  );
}
