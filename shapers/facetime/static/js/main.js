// general functionality

jQuery(function($){

//textarea and input clear default text on focus	
	$("textarea, input").not('input[type="submit"]').focus(function() {
    	if (this.value == this.defaultValue){ this.value = ''; }
	});

	$("textarea, input").blur(function() {
    	if ($.trim(this.value) == ''){ this.value = (this.defaultValue ? this.defaultValue : ''); }
	});
	
	
	//dropdown
	$("select").msDropdown();


});//end jQuery

