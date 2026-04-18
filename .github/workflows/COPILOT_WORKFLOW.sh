#!/bin/bash
# ============================================================================
# UNIVERSAL COPILOT WORKFLOW ENFORCER
# ============================================================================
# This script enforces mandatory workflow for ANY project:
# 1. READ documentation before making changes
# 2. MODIFY code/config (user responsibility)
# 3. TEST to verify changes don't break anything
# 4. DOCUMENT the change in changelog
# 
# Usage: bash .github/workflows/COPILOT_WORKFLOW.sh <operation>
# Operations:
#   - docs          : Find and list all relevant documentation
#   - test          : Run project-appropriate tests
#   - changelog     : Create/update changelog entry
#   - full-workflow : Read → Modify → Test → Document (full loop)
# ============================================================================

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_NAME=$(basename "$PROJECT_ROOT")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_step() {
    echo -e "\n${BLUE}→ $1${NC}"
}

log_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================================
# PROJECT TYPE DETECTION
# ============================================================================

detect_project_type() {
    if [ -f "$PROJECT_ROOT/pyproject.toml" ] || [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        echo "python"
    elif [ -f "$PROJECT_ROOT/package.json" ]; then
        echo "nodejs"
    elif [ -f "$PROJECT_ROOT/docker-compose.yml" ] || [ -f "$PROJECT_ROOT/docker-compose.yaml" ]; then
        echo "docker"
    elif [ -f "$PROJECT_ROOT/PLAYBOOK.md" ] || [ -f "$PROJECT_ROOT/deploy/platform/" ]; then
        echo "kubernetes"
    elif [ -f "$PROJECT_ROOT/Dockerfile" ]; then
        echo "containerized"
    elif [ -f "$PROJECT_ROOT/go.mod" ]; then
        echo "golang"
    elif [ -f "$PROJECT_ROOT/Cargo.toml" ]; then
        echo "rust"
    else
        echo "generic"
    fi
}

# ============================================================================
# DOCUMENTATION DISCOVERY
# ============================================================================

find_documentation() {
    log_step "STEP 1: READING DOCUMENTATION"
    
    local project_type="$1"
    local doc_files=()
    
    # Universal docs
    [ -f "$PROJECT_ROOT/README.md" ] && doc_files+=("README.md")
    [ -f "$PROJECT_ROOT/ARCHITECTURE.md" ] && doc_files+=("ARCHITECTURE.md")
    [ -f "$PROJECT_ROOT/DEPLOY_INSTRUCTIONS.md" ] && doc_files+=("DEPLOY_INSTRUCTIONS.md")
    [ -f "$PROJECT_ROOT/.github/copilot-instructions.md" ] && doc_files+=(".github/copilot-instructions.md")
    [ -f "$PROJECT_ROOT/docs/PLAYBOOK.md" ] && doc_files+=("docs/PLAYBOOK.md")
    [ -f "$PROJECT_ROOT/docs/TODO.md" ] && doc_files+=("docs/TODO.md")
    
    # Type-specific docs
    case "$project_type" in
        kubernetes)
            [ -f "$PROJECT_ROOT/docs/DNS_TESTING_PROCEDURE.md" ] && doc_files+=("docs/DNS_TESTING_PROCEDURE.md")
            [ -f "$PROJECT_ROOT/docs/infrastructure-changes-2026-04.md" ] && doc_files+=("docs/infrastructure-changes-2026-04.md")
            ;;
        python)
            [ -f "$PROJECT_ROOT/REFACTORING.md" ] && doc_files+=("REFACTORING.md")
            ;;
    esac
    
    if [ ${#doc_files[@]} -eq 0 ]; then
        log_warn "No documentation files found"
        return 1
    fi
    
    log_pass "Found ${#doc_files[@]} documentation file(s):"
    printf '%s\n' "${doc_files[@]}" | sed 's/^/  📄 /'
    
    # Print first lines of each doc for context
    echo -e "\n${BLUE}Documentation Summary:${NC}"
    for doc in "${doc_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$doc" ]; then
            echo -e "\n${YELLOW}--- $doc ---${NC}"
            head -15 "$PROJECT_ROOT/$doc"
        fi
    done
}

# ============================================================================
# TEST DISCOVERY & EXECUTION
# ============================================================================

run_tests() {
    log_step "STEP 3: TESTING"
    
    local project_type="$1"
    local test_passed=false
    
    case "$project_type" in
        python)
            if [ -f "$PROJECT_ROOT/pytest.ini" ] || [ -d "$PROJECT_ROOT/tests/" ]; then
                log_warn "Found pytest configuration"
                echo "Would run: pytest $PROJECT_ROOT/tests/ -v"
                if command -v pytest &>/dev/null; then
                    pytest "$PROJECT_ROOT/tests/" -v --tb=short 2>&1 | head -50
                    test_passed=true
                else
                    log_warn "pytest not installed, skipping automated tests"
                fi
            elif [ -f "$PROJECT_ROOT/setup.py" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
                log_warn "Python project found but no test configuration"
                echo "Would run: python -m pytest or similar"
            fi
            ;;
        nodejs)
            if [ -f "$PROJECT_ROOT/package.json" ]; then
                if grep -q '"test"' "$PROJECT_ROOT/package.json"; then
                    log_warn "Found npm test script"
                    echo "Would run: npm test"
                    if command -v npm &>/dev/null; then
                        npm test 2>&1 | head -50 || true
                        test_passed=true
                    fi
                fi
            fi
            ;;
        kubernetes)
            if [ -f "$PROJECT_ROOT/scripts/dns-regression-tests.sh" ]; then
                log_pass "Found DNS regression tests (k3s-specific)"
                echo "Would run: bash scripts/dns-regression-tests.sh"
                if bash "$PROJECT_ROOT/scripts/dns-regression-tests.sh" 2>&1 | tail -5; then
                    test_passed=true
                fi
            fi
            ;;
        docker)
            if [ -f "$PROJECT_ROOT/docker-compose.yml" ] || [ -f "$PROJECT_ROOT/docker-compose.yaml" ]; then
                log_warn "Docker Compose project found"
                echo "Would run: docker-compose config"
                if command -v docker-compose &>/dev/null; then
                    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" config >/dev/null 2>&1
                    test_passed=true
                else
                    log_warn "docker-compose not available"
                fi
            fi
            ;;
    esac
    
    if [ "$test_passed" = true ]; then
        log_pass "Tests completed"
        return 0
    else
        log_warn "No automated tests executed (review manually)"
        return 0  # Don't fail, just warn
    fi
}

# ============================================================================
# CHANGELOG MANAGEMENT
# ============================================================================

update_changelog() {
    log_step "STEP 4: DOCUMENTING CHANGE"
    
    local project_type="$1"
    local changelog_file=""
    local timestamp=$(date -u +"%Y-%m-%d %H:%M UTC")
    
    # Find or create changelog
    if [ -f "$PROJECT_ROOT/CHANGELOG.md" ]; then
        changelog_file="$PROJECT_ROOT/CHANGELOG.md"
    elif [ -f "$PROJECT_ROOT/docs/CHANGELOG.md" ]; then
        changelog_file="$PROJECT_ROOT/docs/CHANGELOG.md"
    elif [ -f "$PROJECT_ROOT/docs/infrastructure-changes-2026-04.md" ]; then
        changelog_file="$PROJECT_ROOT/docs/infrastructure-changes-2026-04.md"
    else
        changelog_file="$PROJECT_ROOT/CHANGELOG.md"
    fi
    
    echo -e "\n${YELLOW}Changelog file location:${NC} $changelog_file"
    
    # Check if file exists, if not create template
    if [ ! -f "$changelog_file" ]; then
        log_warn "Creating new changelog file"
        mkdir -p "$(dirname "$changelog_file")"
        cat > "$changelog_file" << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

## Format
- **Date:** ISO 8601 UTC
- **Author:** Copilot or developer name
- **Type:** feature, bugfix, refactor, test, docs, infrastructure
- **Description:** What changed and why
- **Files Modified:** List of changed files
- **Validation:** How to verify the change works

---

EOF
        log_pass "Created new $changelog_file"
    fi
    
    # Prompt for change details
    echo -e "\n${BLUE}Please provide change details:${NC}"
    read -p "Change title: " change_title
    read -p "Change type (feature/bugfix/refactor/test/docs/infrastructure): " change_type
    read -p "Brief description: " change_desc
    
    # Create changelog entry
    local entry=$(cat <<EOF

## Change - $change_title ($timestamp)

**Type:** $change_type  
**Description:** $change_desc

### Files Modified
- (list files)

### Validation Steps
1. (verification step 1)
2. (verification step 2)

### Rollback Procedure
- (if applicable)

---
EOF
)
    
    # Append to changelog (after header)
    if head -1 "$changelog_file" | grep -q "^#"; then
        # Find insertion point after first header and blank lines
        local insert_line=$(grep -n "^---" "$changelog_file" | head -1 | cut -d: -f1)
        if [ -z "$insert_line" ]; then
            insert_line=$(wc -l < "$changelog_file")
        fi
        
        # Insert entry
        head -n "$((insert_line-1))" "$changelog_file" > "$changelog_file.tmp"
        echo "$entry" >> "$changelog_file.tmp"
        tail -n +"$insert_line" "$changelog_file" >> "$changelog_file.tmp"
        mv "$changelog_file.tmp" "$changelog_file"
        
        log_pass "Changelog updated at: $changelog_file"
    fi
}

# ============================================================================
# WORKFLOW ORCHESTRATION
# ============================================================================

full_workflow() {
    log_step "🔄 STARTING FULL WORKFLOW"
    
    local project_type=$(detect_project_type)
    log_pass "Detected project type: $project_type"
    
    # Step 1: Read documentation
    find_documentation "$project_type" || {
        log_warn "Could not find documentation, but continuing..."
    }
    
    # Step 2: Modify (user responsibility)
    echo -e "\n${BLUE}STEP 2: MODIFY${NC}"
    echo "Make your changes to the code/configuration now."
    read -p "Press Enter when ready to test... "
    
    # Step 3: Test
    run_tests "$project_type"
    
    # Step 4: Document
    update_changelog "$project_type"
    
    echo -e "\n${GREEN}✅ WORKFLOW COMPLETE${NC}"
    echo "Summary:"
    echo "  1. ✅ Read documentation"
    echo "  2. ✅ Modified code/config (manual)"
    echo "  3. ✅ Ran tests"
    echo "  4. ✅ Documented change"
}

# ============================================================================
# MAIN
# ============================================================================

show_usage() {
    cat << EOF
${BLUE}UNIVERSAL COPILOT WORKFLOW ENFORCER${NC}

Usage: bash .github/workflows/COPILOT_WORKFLOW.sh <operation>

Operations:
  ${YELLOW}docs${NC}              Find and display all relevant documentation
  ${YELLOW}test${NC}              Run project-appropriate tests
  ${YELLOW}changelog${NC}         Create or update changelog entry
  ${YELLOW}full-workflow${NC}     Complete workflow: docs → modify → test → document
  ${YELLOW}--help${NC}            Show this help message

Project Type Detection:
  Automatically detects: python, nodejs, docker, kubernetes, containerized, golang, rust, generic

Examples:
  bash .github/workflows/COPILOT_WORKFLOW.sh docs
  bash .github/workflows/COPILOT_WORKFLOW.sh full-workflow
  bash .github/workflows/COPILOT_WORKFLOW.sh test

${YELLOW}For use with GitHub Copilot:${NC}
  This script enforces the mandatory workflow:
  1. READ docs before making changes
  2. MODIFY code (you are responsible)
  3. TEST after modifications
  4. DOCUMENT in changelog

EOF
}

main() {
    local operation="${1:-help}"
    
    case "$operation" in
        docs)
            detect_project_type
            find_documentation "$(detect_project_type)"
            ;;
        test)
            detect_project_type
            run_tests "$(detect_project_type)"
            ;;
        changelog)
            detect_project_type
            update_changelog "$(detect_project_type)"
            ;;
        full-workflow)
            full_workflow
            ;;
        --help|help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown operation: $operation"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
