#!/usr/bin/env ruby

require "yaml"

ROOT = File.expand_path("../../../..", __dir__)
CONFIG_ROOT = File.join(ROOT, "Domains/PR/90-System/Follow-Loop")

config = YAML.safe_load(File.read(File.join(CONFIG_ROOT, "Sources.yml")), aliases: true) || {}
sources = config.fetch("sources", []).select { |item| item["active"] != false }
people = config.fetch("people", [])
institutions = config.fetch("institutions", [])
command = ARGV.shift || "help"
query = ARGV.join(" ").strip.downcase

def state_by_source(config_root)
  lines = File.read(File.join(config_root, "State.md")).lines
  header_index = lines.index { |line| line.start_with?("| source_id |") }
  return {} unless header_index

  headers = lines[header_index].split("|", -1)[1..-2].map(&:strip)
  lines[(header_index + 2)..].to_a.take_while { |line| line.start_with?("|") }.map do |line|
    values = line.split("|", -1)[1..-2].map(&:strip)
    row = headers.zip(values).to_h
    [row["source_id"], row]
  end.to_h
end

def resolved_follow_lane(item)
  return item["follow_lane"] if item["follow_lane"]

  legacy_routes = Array(item["lane"])
  return "ai_follow" if legacy_routes.include?("ai_person")
  return "case_follow" if legacy_routes.include?("comms_case")
  return "luxury_follow" if item.fetch("topics", []).include?("luxury-intelligence")

  "pr_follow"
end

def resolved_routes(item)
  configured = item["routes"] || item["lane"]
  return Array(configured) unless Array(configured).empty?

  {
    "ai_follow" => %w[ai_person],
    "pr_follow" => %w[pr_person pr_signal],
    "case_follow" => %w[case_candidate],
    "embodied_follow" => %w[embodied_entity embodied_signal pr_signal],
    "luxury_follow" => %w[luxury_entity luxury_signal pr_signal]
  }.fetch(resolved_follow_lane(item))
end

def runtime_dump(sources, config_root)
  state = state_by_source(config_root)
  fields = %w[
    id subject_id subject source_kind tier coverage_mode primary_url fallback_url
    query topics follow_lane routes checkpoint_field checkpoint_at last_content_id last_status
  ]
  rows = sources.map do |item|
    state_row = state[item["id"]] || {}
    checkpoint_field = item["coverage_mode"] == "deterministic" ? "scanned_through" : "searched_through"
    checkpoint_at = state_row[checkpoint_field]
    checkpoint_at = nil if checkpoint_at == "—"
    last_content_id = state_row["last_content_id"]
    last_content_id = nil if last_content_id == "—"

    [
      item["id"], item["subject_id"], item["subject"], item["source_kind"], item["tier"],
      item["coverage_mode"], item["primary_url"], item["fallback_url"], item["query"],
      item["topics"], resolved_follow_lane(item), resolved_routes(item), checkpoint_field, checkpoint_at, last_content_id,
      state_row["last_status"]
    ]
  end

  puts YAML.dump(
    "format" => "follow-loop-runtime-v1",
    "matched_count" => sources.length,
    "fields" => fields,
    "sources" => rows
  )
end

def contains?(value, query)
  value.to_s.downcase.include?(query)
end

matched_sources = case command
                  when "person"
                    abort "用法：query_sources.rb person <id-or-name>" if query.empty?
                    matched_people = people.select { |item| contains?(item["id"], query) || contains?(item["name"], query) }
                    ids = matched_people.flat_map { |item| item.fetch("source_ids", []) }
                    subject_ids = matched_people.map { |item| item["id"] }
                    sources.select { |item| ids.include?(item["id"]) || subject_ids.include?(item["subject_id"]) }
                  when "institution"
                    abort "用法：query_sources.rb institution <id-or-name>" if query.empty?
                    matched = institutions.select { |item| contains?(item["id"], query) || contains?(item["name"], query) }
                    ids = matched.flat_map { |item| item.fetch("source_ids", []) }
                    subject_ids = matched.map { |item| item["id"] }
                    sources.select { |item| ids.include?(item["id"]) || subject_ids.include?(item["subject_id"]) }
                  when "topic"
                    abort "用法：query_sources.rb topic <topic-id>" if query.empty?
                    sources.select { |item| item.fetch("topics", []).any? { |topic| contains?(topic, query) } }
                  when "tier"
                    abort "用法：query_sources.rb tier <tier>" if query.empty?
                    sources.select { |item| contains?(item["tier"], query) }
                  when "lane"
                    abort "用法：query_sources.rb lane <follow-lane>" if query.empty?
                    sources.select { |item| contains?(resolved_follow_lane(item), query) }
                  when "source"
                    abort "用法：query_sources.rb source <source-id>" if query.empty?
                    sources.select { |item| contains?(item["id"], query) }
                  when "all"
                    sources
                  when "runtime"
                    sources
                  else
                    abort "命令：person｜institution｜topic｜tier｜lane｜source｜all｜runtime"
                  end

if command == "runtime"
  runtime_dump(matched_sources, CONFIG_ROOT)
  exit
end

state_text = File.read(File.join(CONFIG_ROOT, "State.md"))
ids = matched_sources.map { |item| item["id"] }
state_rows = state_text.lines.select do |line|
  line.start_with?("|") && ids.any? { |id| line.include?("| #{id} |") }
end.map(&:strip)

puts YAML.dump(
  "matched_count" => matched_sources.length,
  "sources" => matched_sources,
  "state_rows" => state_rows
)
