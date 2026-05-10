function claude_usage_status
    set CACHE_FILE "/tmp/claude_usage.cache"
    set CACHE_TTL 600
    
    set FORCE_REFRESH 0
    if contains -- --force $argv; or contains -- -f $argv
        set FORCE_REFRESH 1
    end

    # 1. Logic to check cache age and fetch data
    if test "$FORCE_REFRESH" -eq 0; and test -f "$CACHE_FILE"
        set last_modified (stat -f %m "$CACHE_FILE")
        set now (date +%s)
        set age_seconds (math "$now - $last_modified")

        if test "$age_seconds" -lt "$CACHE_TTL"
            # Calculate age in minutes for the display
            set age_min (math -s0 "$age_seconds / 60")
            # Append the age to the cached content
            echo (cat "$CACHE_FILE") "[$age_min"m"]"
            return
        end
    end

    # 2. Fetch new data (either cache expired or --force used)
    set JSON_DATA (security find-generic-password -s "Claude Code-credentials" -w)
    [ -z "$JSON_DATA" ]; and echo "Token Error"; and return

    set TOKEN (echo $JSON_DATA | jq -r '.claudeAiOauth.accessToken')
    
    set RESULT (curl -s -X GET "https://api.anthropic.com/api/oauth/usage" \
        -H "Authorization: Bearer $TOKEN" \
        -H "anthropic-beta: oauth-2025-04-20" \
        -H "User-Agent: claude-code/2.0.32" --compressed | jq -r '
        def clean_date: sub("\\\.[0-9]+"; "") | sub("\\\+[0-9:]+$"; "Z");
        def time_left(target): (target | clean_date | fromdateiso8601) - now;
        def format_time:
            if . <= 0 then "now"
            elif . < 3600 then ((. / 60 | floor | tostring) + "m")
            else ((. / 3600 | floor | tostring) + "h")
            end;
        "5h(" + (time_left(.five_hour.resets_at) | format_time) + "): " + (.five_hour.utilization | tostring) + "%" +
        " | 7d(" + (time_left(.seven_day.resets_at) | format_time) + "): " + (.seven_day.utilization | tostring) + "%"
    ' 2>/dev/null)

    # 3. Save to cache and output fresh (age is 0m)
    if test -n "$RESULT"
        echo "$RESULT" > "$CACHE_FILE"
        echo "$RESULT [0m]"
    else
        [ -f "$CACHE_FILE" ] && echo (cat "$CACHE_FILE") "[old]" || echo "API Error"
    end
end
