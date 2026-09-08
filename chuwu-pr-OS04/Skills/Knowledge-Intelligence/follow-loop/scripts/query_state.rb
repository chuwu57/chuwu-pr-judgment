#!/usr/bin/env ruby

require "yaml"
require "date"

ROOT = File.expand_path("../../../..", __dir__)
STATE_PATH = File.join(ROOT, "Domains/PR/90-System/Follow-Loop/Case-State.yml")

def load_state
  YAML.safe_load(File.read(STATE_PATH), permitted_classes: [Date, Time], aliases: true) || {}
rescue Errno::ENOENT
  abort "状态文件不存在：#{STATE_PATH}"
end

def print_yaml(value)
  puts YAML.dump(value)
end

state = load_state
cases = state.fetch("tracked_cases", [])
command = ARGV.shift || "summary"

case command
when "summary"
  followups = cases.flat_map { |item| item.fetch("followups", []) }
  watch_items = cases.flat_map { |item| item.fetch("watch_items", []) }
  print_yaml(
    "canonical_keys" => state.dig("deduplication", "canonical_case_keys")&.length || 0,
    "tracked_cases" => cases.length,
    "open_followups" => followups.count { |item| item["status"] == "open" },
    "open_watch_items" => watch_items.count { |item| item["status"] == "open" }
  )
when "due"
  cutoff = Date.parse(ARGV.shift || Date.today.to_s)
  due = []
  cases.each do |item|
    (item.fetch("followups", []) + item.fetch("watch_items", [])).each do |task|
      next unless task["status"] == "open" && task["next_check_at"]
      due << task.merge("parent_case_id" => item["case_id"], "parent_case_name" => item["name"]) if Date.parse(task["next_check_at"].to_s) <= cutoff
    end
  end
  print_yaml(due)
when "case"
  case_id = ARGV.shift or abort "用法：query_state.rb case <case_id>"
  item = cases.find { |candidate| candidate["case_id"] == case_id }
  abort "未找到案例：#{case_id}" unless item
  print_yaml(item)
when "dedup"
  key = ARGV.shift.to_s.strip
  abort "用法：query_state.rb dedup <canonical-key>" if key.empty?
  item = cases.find { |candidate| candidate["canonical_case_key"] == key }
  retained = state.dig("deduplication", "canonical_case_keys")&.include?(key)
  print_yaml("tracked_case" => item, "canonical_key_retained" => retained)
when "open"
  open_cases = cases.each_with_object([]) do |item, result|
    tasks = (item.fetch("followups", []) + item.fetch("watch_items", [])).select { |task| task["status"] == "open" }
    next if tasks.empty?
    result << { "case_id" => item["case_id"], "name" => item["name"], "tasks" => tasks }
  end
  print_yaml(open_cases)
else
  abort "命令：summary｜due [YYYY-MM-DD]｜case <id>｜dedup <key>｜open"
end
