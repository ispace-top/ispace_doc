/**
 * Form Migration Utility
 * Automatically converts old LayUI/PearAdmin classes to modern design system classes
 */

class FormMigration {
    constructor() {
        this.classMap = new Map([
            // Button mappings
            ['layui-btn', 'btn'],
            ['pear-btn', 'btn'],
            ['layui-btn-primary', 'btn-primary'],
            ['pear-btn-primary', 'btn-primary'],
            ['layui-btn-normal', 'btn-secondary'],
            ['pear-btn-secondary', 'btn-secondary'],
            ['layui-btn-warm', 'btn-warning'],
            ['pear-btn-warning', 'btn-warning'],
            ['layui-btn-danger', 'btn-danger'],
            ['pear-btn-danger', 'btn-danger'],
            ['layui-btn-sm', 'btn-sm'],
            ['pear-btn-sm', 'btn-sm'],
            ['layui-btn-lg', 'btn-lg'],
            ['pear-btn-lg', 'btn-lg'],
            
            // Form input mappings
            ['layui-input', 'form-input'],
            ['pear-input', 'form-input'],
            ['layui-textarea', 'form-textarea'],
            ['layui-select', 'form-select'],
            ['pear-select', 'form-select'],
            
            // Form structure mappings
            ['layui-form-item', 'form-group'],
            ['layui-form-label', 'form-label'],
            ['layui-input-inline', 'form-group'],
            ['layui-input-block', 'form-group'],
            ['layui-form-text', 'form-help-text'],
            
            // Card mappings
            ['layui-card', 'card'],
            ['layui-card-header', 'card-header'],
            ['layui-card-body', 'card-body'],
            ['layui-card-footer', 'card-footer'],
            
            // Grid mappings
            ['layui-row', 'form-row'],
            ['layui-col-md6', 'form-group form-group-md'],
            ['layui-col-md4', 'form-group form-group-sm'],
            ['layui-col-md12', 'form-group form-group-lg'],
            
            // Badge mappings
            ['layui-badge', 'badge'],
            ['layui-badge-rim', 'badge badge-outline'],
            ['layui-bg-blue', 'badge-primary'],
            ['layui-bg-green', 'badge-success'],
            ['layui-bg-orange', 'badge-warning'],
            ['layui-bg-red', 'badge-danger']
        ]);
    }

    /**
     * Migrate all elements in the document
     */
    migrateAll() {
        this.migrateForms();
        this.migrateButtons();
        this.migrateCards();
        this.migrateBadges();
        this.addModernInteractions();
    }

    /**
     * Migrate form elements
     */
    migrateForms() {
        // Convert form inputs
        document.querySelectorAll('.layui-input, .pear-input').forEach(input => {
            this.replaceClasses(input, ['layui-input', 'pear-input'], ['form-input']);
        });

        // Convert textareas
        document.querySelectorAll('.layui-textarea').forEach(textarea => {
            this.replaceClasses(textarea, ['layui-textarea'], ['form-textarea']);
        });

        // Convert selects
        document.querySelectorAll('.layui-select, .pear-select').forEach(select => {
            this.replaceClasses(select, ['layui-select', 'pear-select'], ['form-select']);
        });

        // Convert form groups
        document.querySelectorAll('.layui-form-item').forEach(item => {
            this.replaceClasses(item, ['layui-form-item'], ['form-group']);
        });

        // Convert labels
        document.querySelectorAll('.layui-form-label').forEach(label => {
            this.replaceClasses(label, ['layui-form-label'], ['form-label']);
        });
    }

    /**
     * Migrate button elements
     */
    migrateButtons() {
        document.querySelectorAll('.layui-btn, .pear-btn').forEach(button => {
            const oldClasses = Array.from(button.classList);
            const newClasses = ['btn'];

            // Map button variants
            if (oldClasses.includes('layui-btn-primary') || oldClasses.includes('pear-btn-primary')) {
                newClasses.push('btn-primary');
            } else if (oldClasses.includes('layui-btn-normal') || oldClasses.includes('pear-btn-secondary')) {
                newClasses.push('btn-secondary');
            } else if (oldClasses.includes('layui-btn-warm') || oldClasses.includes('pear-btn-warning')) {
                newClasses.push('btn-warning');
            } else if (oldClasses.includes('layui-btn-danger') || oldClasses.includes('pear-btn-danger')) {
                newClasses.push('btn-danger');
            }

            // Map button sizes
            if (oldClasses.includes('layui-btn-sm') || oldClasses.includes('pear-btn-sm')) {
                newClasses.push('btn-sm');
            } else if (oldClasses.includes('layui-btn-lg') || oldClasses.includes('pear-btn-lg')) {
                newClasses.push('btn-lg');
            }

            // Replace old classes with new ones
            const classesToRemove = oldClasses.filter(cls => 
                cls.startsWith('layui-btn') || cls.startsWith('pear-btn')
            );
            
            this.replaceClasses(button, classesToRemove, newClasses);
        });
    }

    /**
     * Migrate card elements
     */
    migrateCards() {
        document.querySelectorAll('.layui-card').forEach(card => {
            this.replaceClasses(card, ['layui-card'], ['card']);
        });

        document.querySelectorAll('.layui-card-header').forEach(header => {
            this.replaceClasses(header, ['layui-card-header'], ['card-header']);
        });

        document.querySelectorAll('.layui-card-body').forEach(body => {
            this.replaceClasses(body, ['layui-card-body'], ['card-body']);
        });
    }

    /**
     * Migrate badge elements
     */
    migrateBadges() {
        document.querySelectorAll('.layui-badge, .layui-badge-rim').forEach(badge => {
            const oldClasses = Array.from(badge.classList);
            const newClasses = ['badge'];

            if (oldClasses.includes('layui-badge-rim')) {
                newClasses.push('badge-outline');
            }

            // Map color classes
            if (oldClasses.includes('layui-bg-blue')) {
                newClasses.push('badge-primary');
            } else if (oldClasses.includes('layui-bg-green')) {
                newClasses.push('badge-success');
            } else if (oldClasses.includes('layui-bg-orange')) {
                newClasses.push('badge-warning');
            } else if (oldClasses.includes('layui-bg-red')) {
                newClasses.push('badge-danger');
            }

            const classesToRemove = oldClasses.filter(cls => 
                cls.startsWith('layui-badge') || cls.startsWith('layui-bg-')
            );
            
            this.replaceClasses(badge, classesToRemove, newClasses);
        });
    }

    /**
     * Add modern interactions to forms
     */
    addModernInteractions() {
        // Add floating labels
        this.addFloatingLabels();
        
        // Add form validation styling
        this.addFormValidation();
        
        // Add search box enhancements
        this.addSearchEnhancements();
        
        // Add loading states to buttons
        this.addButtonLoadingStates();
    }

    /**
     * Add floating label effect to form groups
     */
    addFloatingLabels() {
        document.querySelectorAll('.form-group').forEach(group => {
            const label = group.querySelector('.form-label');
            const input = group.querySelector('.form-input, .form-textarea, .form-select');
            
            if (label && input && !group.classList.contains('floating-label')) {
                group.classList.add('floating-label');
                
                // Add floating label styles if not already present
                if (!document.getElementById('floating-label-styles')) {
                    const style = document.createElement('style');
                    style.id = 'floating-label-styles';
                    style.textContent = `
                        .floating-label {
                            position: relative;
                            margin-top: var(--space-4);
                        }
                        
                        .floating-label .form-label {
                            position: absolute;
                            top: 0;
                            left: var(--space-4);
                            transform: translateY(-50%);
                            background: var(--bg-primary);
                            padding: 0 var(--space-1);
                            font-size: var(--text-xs);
                            color: var(--text-tertiary);
                            transition: all var(--transition-fast);
                            pointer-events: none;
                        }
                        
                        .floating-label .form-input:focus + .form-label,
                        .floating-label .form-textarea:focus + .form-label,
                        .floating-label .form-select:focus + .form-label {
                            color: var(--brand-primary);
                            font-weight: var(--font-weight-medium);
                        }
                    `;
                    document.head.appendChild(style);
                }
            }
        });
    }

    /**
     * Add modern form validation
     */
    addFormValidation() {
        document.querySelectorAll('form').forEach(form => {
            // Skip forms that should not be validated by this general handler
            // Specifically exclude the login form to prevent interference
            if (form.hasAttribute('data-validate') && form.getAttribute('data-validate') === 'false') {
                return;
            }
            
            form.addEventListener('submit', (e) => {
                const inputs = form.querySelectorAll('.form-input, .form-textarea, .form-select');
                let isValid = true;

                inputs.forEach(input => {
                    if (input.hasAttribute('required') && !input.value.trim()) {
                        input.classList.add('error');
                        isValid = false;
                    } else {
                        input.classList.remove('error');
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                }
            });
        });
    }

    /**
     * Add search box enhancements
     */
    addSearchEnhancements() {
        document.querySelectorAll('input[type="text"][placeholder*="搜索"], input[type="search"]').forEach(input => {
            if (!input.parentElement.classList.contains('search-box')) {
                // Wrap input in search-box container
                const searchBox = document.createElement('div');
                searchBox.className = 'search-box';
                
                const searchIcon = document.createElement('svg');
                searchIcon.className = 'search-icon';
                searchIcon.innerHTML = '<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>';
                searchIcon.setAttribute('viewBox', '0 0 20 20');
                searchIcon.setAttribute('fill', 'currentColor');
                
                input.parentNode.insertBefore(searchBox, input);
                searchBox.appendChild(searchIcon);
                searchBox.appendChild(input);
                
                input.classList.add('search-input');
            }
        });
    }

    /**
     * Add loading states to form submission buttons
     */
    addButtonLoadingStates() {
        document.querySelectorAll('form').forEach(form => {
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            
            form.addEventListener('submit', () => {
                submitButtons.forEach(button => {
                    if (button.tagName.toLowerCase() === 'button') {
                        button.classList.add('btn-loading');
                        button.disabled = true;
                        
                        // Remove loading state after 3 seconds (fallback)
                        setTimeout(() => {
                            button.classList.remove('btn-loading');
                            button.disabled = false;
                        }, 3000);
                    }
                });
            });
        });
    }

    /**
     * Replace classes on an element
     */
    replaceClasses(element, oldClasses, newClasses) {
        oldClasses.forEach(cls => element.classList.remove(cls));
        newClasses.forEach(cls => element.classList.add(cls));
    }

    /**
     * Auto-migrate forms based on data attributes
     */
    autoMigrate() {
        // Look for data-migrate attribute
        document.querySelectorAll('[data-migrate="true"]').forEach(element => {
            this.migrateElement(element);
        });
        
        // Auto-detect and migrate common patterns
        this.autoDetectPatterns();
    }

    /**
     * Auto-detect common LayUI patterns and migrate them
     */
    autoDetectPatterns() {
        // Detect LayUI form structure
        document.querySelectorAll('.layui-form').forEach(form => {
            form.classList.add('modern-form');
            this.migrateForms();
        });

        // Detect button groups
        document.querySelectorAll('.layui-btn-group').forEach(group => {
            group.classList.remove('layui-btn-group');
            group.classList.add('btn-group');
        });
    }
}

// Initialize form migration when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.enableFormMigration !== false) {
        const migration = new FormMigration();
        migration.migrateAll();
        
        // Watch for dynamically added content
        if (window.MutationObserver) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                // Check if the added node or its children need migration
                                if (node.classList && (
                                    node.classList.contains('layui-btn') ||
                                    node.classList.contains('pear-btn') ||
                                    node.classList.contains('layui-input') ||
                                    node.classList.contains('layui-form')
                                )) {
                                    migration.migrateAll();
                                }
                            }
                        });
                    }
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    }
});

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormMigration;
}

// Make available globally
window.FormMigration = FormMigration;