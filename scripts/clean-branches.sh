#!/bin/bash
# Clean up merged and stale branches

echo "🧹 Cleaning up Git branches..."

# 1. Fetch latest from remote
echo "📡 Fetching remote branches..."
git fetch --prune

# 2. Delete merged local branches (except main and current)
echo "🗑️  Deleting merged local branches..."
git branch --merged main | grep -v '^\*\|main\|master\|develop' | while read branch; do
    echo "  Deleting: $branch"
    git branch -d "$branch"
done

# 3. Delete remote branches that no longer exist
echo "🌐 Pruning remote tracking branches..."
git remote prune origin

# 4. Show remaining branches
echo ""
echo "📋 Remaining branches:"
git branch -a | sed 's/^/  /'

echo ""
echo "✅ Cleanup complete!"
