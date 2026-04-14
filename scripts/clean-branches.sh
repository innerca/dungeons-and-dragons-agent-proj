#!/bin/bash
# Clean up merged and stale branches with automatic scheduling

BRANCH_CLEANUP_STATE=".git/branch-cleanup-state"
CLEANUP_INTERVAL_DAYS=7  # Run cleanup every 7 days

# Check if cleanup is needed
check_cleanup_needed() {
    if [ ! -f "$BRANCH_CLEANUP_STATE" ]; then
        return 0  # No state file, cleanup needed
    fi
    
    last_cleanup=$(cat "$BRANCH_CLEANUP_STATE")
    current_time=$(date +%s)
    
    # Calculate days since last cleanup
    days_since=$(( (current_time - last_cleanup) / 86400 ))
    
    if [ $days_since -ge $CLEANUP_INTERVAL_DAYS ]; then
        return 0  # Cleanup needed
    else
        echo "⏭️  Last cleanup was ${days_since} days ago. Next cleanup in $((CLEANUP_INTERVAL_DAYS - days_since)) days."
        return 1  # Skip cleanup
    fi
}

# Record cleanup time
record_cleanup_time() {
    date +%s > "$BRANCH_CLEANUP_STATE"
    echo "📅 Cleanup time recorded: $(date '+%Y-%m-%d %H:%M:%S')"
}

# Skip if not needed (unless forced)
if [ "$1" != "--force" ] && ! check_cleanup_needed; then
    exit 0
fi

echo "🧹 Cleaning up Git branches..."
echo ""

# 1. Fetch latest from remote
echo "📡 Fetching remote branches..."
git fetch --prune

# 2. Delete merged local branches (except main and current)
echo "🗑️  Deleting merged local branches..."
deleted_count=0
git branch --merged main | grep -v '^\*\|main\|master\|develop' | while read branch; do
    echo "  Deleting: $branch"
    git branch -d "$branch"
    deleted_count=$((deleted_count + 1))
done

# 3. Delete remote branches that no longer exist
echo "🌐 Pruning remote tracking branches..."
git remote prune origin

# 4. Record cleanup time
record_cleanup_time

# 5. Show remaining branches
echo ""
echo "📋 Remaining branches:"
git branch -a | sed 's/^/  /'

echo ""
echo "✅ Cleanup complete! Next scheduled cleanup in ${CLEANUP_INTERVAL_DAYS} days."
echo "   (Use --force to run immediately)"
