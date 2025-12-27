frappe.pages['customer-display'].on_page_load = function(wrapper) {

	const pos_profile = frappe.utils.get_url_arg("pos_profile");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: '',
		single_column: true
	});

	// Inject new layout
	$(page.main).html(`
		<div style="
			display: flex;
			height: 100vh;
			width: 100vw;
			background: #f9f9f9;
			font-family: 'Inter', sans-serif;
			overflow: hidden;
		">
			<!-- Left Side: Logo and Ad Area -->
			<div style="
				width: 70%;
				padding: 2rem;
				display: flex;
				flex-direction: column;
				align-items: center;
				justify-content: flex-start;
				box-sizing: border-box;
				border-right: 2px solid #eee;
			">
				<img src="/assets/customer_display/images/Logo_ALAN_noSpace.png" alt="Logo" style="max-width: 170px; margin-bottom: 2rem;" />
				
				<div id="promo-space" style="
				    width: 100%;
				    background: #fff3e0;
				    border: 2px dashed #ffa726;
				    border-radius: 16px;
				    display: flex;
				    align-items: center;
				    justify-content: center;
				    color: #ff9800;
				    font-weight: 600;
				    font-size: 1.2rem;
				    overflow: hidden;
				">
				    Loading Ads...
				</div>
			</div>

			<!-- Right Side: Cart -->
			<div style="
				width: 30%;
				padding: 2rem;
				display: flex;
				justify-content: center;
				align-items: center;
				box-sizing: border-box;
			">
				<!-- Cart Box -->
				<div style="
					flex: 1;
					display: flex;
					flex-direction: column;
					justify-content: space-between;
					max-width: 600px;
					background: #fff;
					border-radius: 16px;
					box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
					border: 1px solid #ccc;
					padding: 1rem 1.5rem;
					height: 75%;
					box-sizing: border-box;
				">

					<!-- Customer Info -->
                    <div id="customer-info" style="margin-bottom: 1rem;">
                        <div style="font-size: 1.2rem; font-weight: 600;">
                            Hi, <span id="customer_name">Guest</span>
							<br>
							<span style="font-size:75%;font-weight: 400;">Saya <b><span id="staff_name">–</span></b> siap membantu Anda<span style="font-size:75%">
                        </div>
                        <div style="font-size: 1rem; color: #666;">
                            <span style="font-size:75%;font-weight: 400;"> Your current points: <span id="customer_points">0</span> </span>
                        </div>
                    </div>

					<!-- Cart Header -->
					<div style="font-weight: 600; font-size: 1.2rem; margin-bottom: 0.5rem; border-bottom: 1px solid #eee; padding-bottom: 0.5rem;">
						Item Cart
					</div>

					<!-- Scrollable Item List -->
					<div id="cart-items" style="
						flex-grow: 1;
						overflow-y: auto;
						margin-bottom: 1rem;
					">
						<!-- Items injected by JS -->
					</div>

					<!-- Cart Summary -->
					<div style="
						border-top: 1px solid #ddd;
						padding-top: 1rem;
						font-size: 1rem;
					">
						<div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
							<span style="color: #666;">Total Quantity</span>
							<strong id="total-qty">0</strong>
						</div>
						<div style="display: flex; justify-content: space-between;">
							<span style="color: #666;">Total</span>
							<strong id="total-price">Rp 0</strong>
						</div>
					</div>

					<!-- New: Paid & Change -->
				    <div style="margin-top: 0.5rem; width: 100%;">
				        <div style="display: flex; justify-content: space-between; font-size: 1rem; color: #333;">
				            <div>Paid:</div>
				            <div> <span id="paid_amount" style="text-align: right; display: inline-block; min-width: 100px;">Rp 0</span></div>
				        </div>
				        <div style="display: flex; justify-content: space-between; font-size: 1rem; color: #333; margin-top: 0.25rem;">
				            <div>Change:</div>
				            <div> <span id="change_amount" style="text-align: right; display: inline-block; min-width: 100px;">Rp 0</span></div>
				        </div>
				    </div>

				</div>
			</div>
		</div>
	`);

	// Style override
	if (location.pathname.includes("customer-display")) {
		const style = document.createElement("style");
		style.innerHTML = `
			.container {
				max-width: 100vw !important;
				width: 100% !important;
				padding-left: 0 !important;
				padding-right: 0 !important;
			}
		`;
		document.head.appendChild(style);
	}

	// Hide Frappe UI shell
	setTimeout(() => {
		$(`.navbar, .layout-side-section, .page-head, .page-actions, header, #navbar, .sidebar, .module-sidebar`).hide();
		$('body').css("background", "#fff");
		document.body.style.overflow = "hidden";
	}, 300);

	// Render cart items
	function renderCart(items) {
		const container = document.getElementById("cart-items");
		if (!container) return;

		container.innerHTML = "";

		let total_qty = 0;
		let total_price = 0;

		if (!items.length) {
			container.innerHTML = '<p style="color: #aaa;">Cart is empty.</p>';
			document.getElementById("total-qty").textContent = "0";
			document.getElementById("total-price").textContent = "Rp 0";
			return;
		}

		items.forEach(item => {
			total_qty += item.qty;
			total_price += item.qty * item.rate;

			const div = document.createElement("div");
			div.style = "display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #eee;";
			div.innerHTML = `
				<div style="font-weight: 500;">
					${item.item_name}
					<div style="font-size: 0.85rem; color: #777;">${item.item_code}</div>
				</div>
				<div style="text-align: right;">
					<div>${item.qty} × Rp ${item.rate.toLocaleString("id-ID")}</div>
					<div style="font-weight: bold;">Rp ${(item.qty * item.rate).toLocaleString("id-ID")}</div>
				</div>
			`;
			container.appendChild(div);
		});

		document.getElementById("total-qty").textContent = total_qty;
		document.getElementById("total-price").textContent = `Rp ${total_price.toLocaleString("id-ID")}`;
	}

	function renderAds(images) {
	    const container = document.getElementById("promo-space");
	    if (!container) return;

	    container.innerHTML = "";

	    if (!images.length) {
	        container.innerHTML = `<p style="color: #aaa;">No ads available.</p>`;
	        return;
	    }

	    if (images.length === 1) {
	        // Just show one image
	        const img = document.createElement("img");
	        img.src = images[0].image;
	        img.style = "max-width: 100%; max-height: 100%; object-fit: contain;";
	        container.appendChild(img);
	        return;
	    }

	    // Rotation logic
	    let currentIndex = 0;

	    const img = document.createElement("img");
	    img.src = images[0].image;
	    img.style = "max-width: 100%; max-height: 100%; object-fit: contain; transition: opacity 0.5s ease;";
	    container.appendChild(img);

	    setInterval(() => {
	        currentIndex = (currentIndex + 1) % images.length;
	        img.style.opacity = 0;
	        setTimeout(() => {
	            img.src = images[currentIndex].image;
	            img.style.opacity = 1;
	        }, 500);
	    }, 5000); // Rotate every 5 seconds
	}

	// Fetch and render ads
	frappe.call({
	    method: "customer_display.customer_display.doctype.pos_ads.pos_ads.get_pos_ads",
	    callback: function (r) {
	        renderAds(r.message || []);
	    }
	});

	// ─────────────── Poll for current settings ───────────────

    let last_customer = "";  
    let last_points = -1;
    let last_paid_amount = -1;
    let last_change_amount = -1;

    function fetch_and_update_customer() {
        frappe.call({
	        method: "customer_display.api.get_customer_display_settings",
	        args: { pos_profile },
	        callback: (r) => {
	            // r.message is { customer: "...", points: N, paid_amount: X, change_amount: Y }
	            const data = r.message || {
	                customer: "",
	                points: 0,
	                paid_amount: 0,
	                change_amount: 0
	            };

	            const cust    = data.customer        || "";
	            const pts     = data.points          || 0;
	            const paid    = data.paid_amount     != null ? data.paid_amount : 0;
	            const change  = data.change_amount   != null ? data.change_amount : 0;

	            // Update customer name
	            if (cust !== last_customer) {
	                document.getElementById("customer_name").innerText = cust || "Guest";
	                last_customer = cust;
	            }
	            // Update loyalty points
	            if (pts !== last_points) {
	                document.getElementById("customer_points").innerText = pts;
	                last_points = pts;
	            }
	        }
	    });
    }

    function fetch_and_update_customer_paid() {
        frappe.call({
	        method: "customer_display.api.get_customer_display_settings",
	        args: { pos_profile },
	        callback: (r) => {
	            // r.message is { customer: "...", points: N, paid_amount: X, change_amount: Y }
	            const data = r.message || {
	                customer: "",
	                points: 0,
	                paid_amount: 0,
	                change_amount: 0
	            };

	            const cust    = data.customer        || "";
	            const pts     = data.points          || 0;
	            const paid    = data.paid_amount     != null ? data.paid_amount : 0;
	            const change  = data.change_amount   != null ? data.change_amount : 0;

	            // Update paid amount
	            if (paid !== last_paid_amount) {
	                document.getElementById("paid_amount").innerText = "Rp " + paid.toLocaleString("id-ID");
    				last_paid_amount = paid;
	            }
	            // Update change amount
	            if (change !== last_change_amount) {
	                document.getElementById("change_amount").innerText = "Rp " + change.toLocaleString("id-ID");
    				last_change_amount = change;
	            }
	        }
	    });
    }


    function fetch_and_update_item_cart(){
    	frappe.call({
			method: "customer_display.api.get_customer_display",
			args: { pos_profile },
			callback: function (r) {
				renderCart(r.message || []);
			}
		});
    }

    frappe.realtime.on("customer_display_customer_" + pos_profile, function () {
	    fetch_and_update_customer();
	});
	frappe.realtime.on("update_customer_display_" + pos_profile, function () {
	    fetch_and_update_item_cart();
	});
	frappe.realtime.on("update_customer_display_paid_" + pos_profile, function () {
	    fetch_and_update_customer_paid();
	});

	// Load once
	frappe.call({
		method: "customer_display.api.clear_customer_display",
		args: { pos_profile },
		callback: function (r) {
			renderCart(r.message || []);
			fetch_and_update_customer();
        	fetch_and_update_customer_paid();
		}
	});

	frappe.call({
	  method: "frappe.client.get_value",
	  args: {
	    doctype: "User",
	    filters: { name: frappe.session.user },
	    fieldname: ["full_name"]
	  },
	  callback: r => {
	    if (r.message && r.message.full_name) {
	      document.getElementById("staff_name").innerText = r.message.full_name;
	    }
	  }
	});
};
