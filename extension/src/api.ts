const API_BASE = "http://localhost:8000/api";

export interface School {
  id: string;
  legacy_id: number | null;
  name: string;
  city: string | null;
  state: string | null;
}

export interface Tag {
  tagName: string;
  tagCount: number;
}

export interface Professor {
  id: string;
  legacy_id: number | null;
  school_id: string;
  first_name: string;
  last_name: string;
  department: string | null;
  avg_rating: number | null;
  avg_difficulty: number | null;
  num_ratings: number;
  would_take_again_percent: number | null;
  tags: Tag[];
  courses: string[];
  rmp_link: string | null;
}

export interface SearchResponse {
  results: Professor[];
  total: number;
  limit: number;
  offset: number;
}

export interface Rating {
  id: string | null;
  legacy_id: number | null;
  course: string | null;
  comment: string | null;
  clarity_rating: number | null;
  difficulty_rating: number | null;
  helpful_rating: number | null;
  date: string | null;
  grade: string | null;
  is_for_credit: boolean | null;
  is_online: boolean | null;
  attendance_mandatory: string | null;
  rating_tags: string | null;
  would_take_again: number | null;
  thumbs_up: number;
  thumbs_down: number;
}

export interface ProfessorDetail {
  id: string;
  legacy_id: number | null;
  first_name: string;
  last_name: string;
  department: string | null;
  avg_rating: number | null;
  avg_difficulty: number | null;
  num_ratings: number;
  would_take_again_percent: number | null;
  tags: Tag[];
  rmp_link: string | null;
  school_name: string | null;
  ratings: Rating[];
}

export interface BootstrapStatus {
  school_id: string;
  school_name: string;
  status: string;
  professor_count: number;
}

export interface SearchFilters {
  school_id: string;
  q?: string;
  department?: string;
  min_rating?: number;
  max_difficulty?: number;
  min_would_take_again?: number;
  min_num_ratings?: number;
  tag?: string;
  course?: string;
  sort_by?: string;
  sort_order?: string;
  limit?: number;
  offset?: number;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function searchSchools(query: string): Promise<School[]> {
  return fetchApi<School[]>(`/schools/search?q=${encodeURIComponent(query)}`);
}

export async function getSavedSchools(): Promise<School[]> {
  return fetchApi<School[]>("/schools");
}

export async function bootstrapSchool(schoolId: string): Promise<BootstrapStatus> {
  return fetchApi<BootstrapStatus>(`/schools/${encodeURIComponent(schoolId)}/bootstrap`, {
    method: "POST",
  });
}

export async function getDepartments(schoolId: string): Promise<string[]> {
  return fetchApi<string[]>(`/schools/${encodeURIComponent(schoolId)}/departments`);
}

export async function getTags(schoolId: string): Promise<string[]> {
  return fetchApi<string[]>(`/schools/${encodeURIComponent(schoolId)}/tags`);
}

export async function searchProfessors(filters: SearchFilters): Promise<SearchResponse> {
  const params = new URLSearchParams();
  params.set("school_id", filters.school_id);
  if (filters.q) params.set("q", filters.q);
  if (filters.department) params.set("department", filters.department);
  if (filters.min_rating !== undefined) params.set("min_rating", String(filters.min_rating));
  if (filters.max_difficulty !== undefined) params.set("max_difficulty", String(filters.max_difficulty));
  if (filters.min_would_take_again !== undefined) params.set("min_would_take_again", String(filters.min_would_take_again));
  if (filters.min_num_ratings !== undefined) params.set("min_num_ratings", String(filters.min_num_ratings));
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.course) params.set("course", filters.course);
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.sort_order) params.set("sort_order", filters.sort_order);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  return fetchApi<SearchResponse>(`/professors/search?${params.toString()}`);
}

export async function getProfessorDetail(professorId: string): Promise<ProfessorDetail> {
  return fetchApi<ProfessorDetail>(`/professors/${encodeURIComponent(professorId)}`);
}
