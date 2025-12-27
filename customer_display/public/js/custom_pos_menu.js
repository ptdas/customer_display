// function add_custom_pos_container() {
//     const customer_cart = $('.customer-cart-container');
//     if (customer_cart.length) {
//         if ($('#custom-menu-container').length === 0) {
//             const new_container = $(`
//                 <div id="custom-menu-container"></div>
//             `);

//             new_container.css({
//                 'background': '#ffffff',
//                 'border': '1px solid #dcdcdc',
//                 'padding': '20px',
//                 'margin-bottom': '10px',
//                 'border-radius': '4px',
//                 'box-shadow': 'none'
//             });

//             customer_cart.prepend(new_container);

//             new_container.append(`
//                 <div class="form-check mb-2">
//                     <input type="checkbox" class="form-check-input" id="b2b-checkbox">
//                     <label class="form-check-label" for="b2b-checkbox">B2B</label>
//                 </div>
//                 <div id="b2b-fields" style="display:none; margin-top: 10px;">
//                     <div class="form-group">
//                         <label for="b2b-address">Alamat B2B</label>
//                         <input type="text" class="form-control" id="b2b-address" placeholder="Masukkan alamat...">
//                     </div>
//                     <div class="form-check">
//                         <input type="checkbox" class="form-check-input" id="invoice-checkbox">
//                         <label class="form-check-label" for="invoice-checkbox">Minta Faktur?</label>
//                     </div>
//                 </div>
//             `);



//             $('#b2b-checkbox').on('change', function() {
//                 if ($(this).is(':checked')) {
//                     $('#b2b-fields').slideDown();
//                 } else {
//                     $('#b2b-fields').slideUp();
//                     $('#b2b-address').val('');
//                     $('#invoice-checkbox').prop('checked', false);
//                 }
//             });

//         }
//     } else {
//         setTimeout(add_custom_pos_container, 200);
//     }
// }

// add_custom_pos_container();

