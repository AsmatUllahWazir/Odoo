/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Website Property Search Widget
 */
export class WebsitePropertySearch extends Component {
    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            searchTerm: "",
            filters: {
                type: "",
                minPrice: "",
                maxPrice: "",
                bedrooms: "",
            },
            results: [],
            loading: false,
            totalCount: 0,
        });
    }

    async performSearch() {
        this.state.loading = true;
        try {
            const params = {
                search: this.state.searchTerm,
                type: this.state.filters.type,
                min_price: this.state.filters.minPrice,
                max_price: this.state.filters.maxPrice,
                bedrooms: this.state.filters.bedrooms,
            };

            const result = await this.rpc("/property/search", params);

            this.state.results = result.properties || [];
            this.state.totalCount = result.count || 0;

            // Update URL with search parameters
            const searchParams = new URLSearchParams();
            if (this.state.searchTerm) searchParams.set("search", this.state.searchTerm);
            if (this.state.filters.type) searchParams.set("type", this.state.filters.type);
            if (this.state.filters.minPrice) searchParams.set("min_price", this.state.filters.minPrice);
            if (this.state.filters.maxPrice) searchParams.set("max_price", this.state.filters.maxPrice);
            if (this.state.filters.bedrooms) searchParams.set("bedrooms", this.state.filters.bedrooms);

            const newUrl = `${window.location.pathname}?${searchParams.toString()}`;
            window.history.pushState({}, "", newUrl);

        } catch (error) {
            console.error("Search error:", error);
            this.notification.add("Error performing search", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    clearFilters() {
        this.state.filters = {
            type: "",
            minPrice: "",
            maxPrice: "",
            bedrooms: "",
        };
        this.state.searchTerm = "";
        this.performSearch();
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            this.performSearch();
        }
    }
}

WebsitePropertySearch.template = "smart_property_lifecycle.WebsitePropertySearch";

registry.category("website").add("property_search", WebsitePropertySearch);

/**
 * Schedule Viewing Button
 */
export class ScheduleViewingButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
    }

    async scheduleViewing(propertyId) {
        try {
            // Open viewing scheduling wizard
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Schedule Viewing",
                res_model: "property.viewing",
                view_mode: "form",
                target: "new",
                context: {
                    default_property_id: propertyId,
                },
            });
        } catch (error) {
            console.error("Error scheduling viewing:", error);
            this.notification.add("Error scheduling viewing", {
                type: "danger",
            });
        }
    }
}

ScheduleViewingButton.template = "smart_property_lifecycle.ScheduleViewingButton";

/**
 * Save Property Button (Favorites)
 */
export class SavePropertyButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.session = useService("session");

        this.state = useState({
            saved: false,
            loading: false,
        });
    }

    async willStart() {
        if (this.props.propertyId && this.session.userId) {
            await this.checkIfSaved();
        }
    }

    async checkIfSaved() {
        try {
            const saved = await this.orm.call(
                "property.property",
                "is_saved_by_user",
                [this.props.propertyId],
                {}
            );
            this.state.saved = saved;
        } catch (error) {
            console.error("Error checking saved status:", error);
        }
    }

    async toggleSave() {
        if (!this.session.userId) {
            this.notification.add("Please login to save properties", {
                type: "warning",
            });
            return;
        }

        this.state.loading = true;
        try {
            if (this.state.saved) {
                await this.orm.call(
                    "property.property",
                    "remove_from_favorites",
                    [this.props.propertyId],
                    {}
                );
                this.state.saved = false;
                this.notification.add("Property removed from favorites", {
                    type: "success",
                });
            } else {
                await this.orm.call(
                    "property.property",
                    "add_to_favorites",
                    [this.props.propertyId],
                    {}
                );
                this.state.saved = true;
                this.notification.add("Property saved to favorites", {
                    type: "success",
                });
            }
        } catch (error) {
            console.error("Error toggling save:", error);
            this.notification.add("Error updating favorites", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }
}

SavePropertyButton.template = "smart_property_lifecycle.SavePropertyButton";

/**
 * Quick View Gallery
 */
export class PropertyGallery extends Component {
    setup() {
        this.state = useState({
            currentIndex: 0,
            images: this.props.images || [],
            showModal: false,
        });
    }

    nextImage() {
        if (this.state.currentIndex < this.state.images.length - 1) {
            this.state.currentIndex++;
        }
    }

    prevImage() {
        if (this.state.currentIndex > 0) {
            this.state.currentIndex--;
        }
    }

    openGallery(index = 0) {
        this.state.currentIndex = index;
        this.state.showModal = true;
    }

    closeGallery() {
        this.state.showModal = false;
    }
}

PropertyGallery.template = "smart_property_lifecycle.PropertyGallery";

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function() {
    // Schedule viewing buttons
    document.querySelectorAll(".schedule-viewing").forEach(function(btn) {
        btn.addEventListener("click", function() {
            const propertyId = this.getAttribute("data-property-id");
            if (propertyId) {
                // Trigger Odoo action
                odoo.define("schedule_viewing", function() {
                    const action = {
                        type: "ir.actions.act_window",
                        name: "Schedule Viewing",
                        res_model: "property.viewing",
                        view_mode: "form",
                        target: "new",
                        context: {
                            default_property_id: parseInt(propertyId),
                        },
                    };
                    odoo.actions.doAction(action);
                });
            }
        });
    });

    // Property filters form submission
    const filterForm = document.querySelector(".property-filters-form");
    if (filterForm) {
        filterForm.addEventListener("submit", function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const params = new URLSearchParams();

            for (const [key, value] of formData.entries()) {
                if (value) {
                    params.set(key, value);
                }
            }

            window.location.href = `/property?${params.toString()}`;
        });
    }
});