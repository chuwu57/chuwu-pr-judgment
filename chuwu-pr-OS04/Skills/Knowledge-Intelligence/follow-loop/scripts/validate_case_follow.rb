#!/usr/bin/env ruby

require "yaml"
require "date"

root = File.expand_path("../../../..", __dir__)
path = File.join(root, "Domains/PR/90-System/Follow-Loop/Case-State.yml")
state = YAML.safe_load(File.read(path), permitted_classes: [Date, Time], aliases: true) || {}
errors = []

keys = state.dig("deduplication", "canonical_case_keys") || []
cases = state.fetch("tracked_cases", [])
errors << "canonical_case_keys存在重复" unless keys.length == keys.uniq.length

ids = cases.map { |item| item["case_id"] }
errors << "tracked_cases的case_id缺失或重复" if ids.any?(&:nil?) || ids.length != ids.uniq.length

cases.each do |item|
  %w[case_id name organization canonical_case_key source_urls knowledge_deposited knowledge_paths].each do |field|
    errors << "#{item['case_id'] || 'unknown'}缺少#{field}" unless item.key?(field)
  end
  errors << "#{item['case_id']}未保留canonical_case_key" unless keys.include?(item["canonical_case_key"])
  errors << "#{item['case_id']}缺少来源URL" if item.fetch("source_urls", []).empty?
  item.fetch("knowledge_paths", []).each do |relative|
    errors << "知识路径不存在：#{relative}" unless File.exist?(File.join(root, relative))
  end
  (item.fetch("followups", []) + item.fetch("watch_items", [])).each do |task|
    errors << "#{item['case_id']}任务status非法" unless %w[open closed discarded].include?(task["status"])
    begin
      Date.parse(task["next_check_at"].to_s) if task["status"] == "open" && task["next_check_at"]
    rescue Date::Error
      errors << "#{item['case_id']}任务next_check_at非法"
    end
  end
end

if errors.empty?
  puts "PASS: Follow Loop Case Follow（#{cases.length}个跟踪案例，#{keys.length}个去重键）"
  exit 0
end

puts "FAIL: Follow Loop Case Follow"
errors.each { |error| puts "- #{error}" }
exit 1
