function AboutYou($form) {
	var self = this;

	$form.submit(function(e) {
		var email = $form.find(".js-form-email").val();
		console.log("identifying this user as " + email);
		window.analytics.identify(email);
	});

	$form.validate({
		errorElement: 'div',
		rules: {
			name: {
				required: true
			},
			email: {
				required: true,
				email: true
			}
		},
		messages: {
			name: 'Please enter your full name.',
			email: 'Please enter your email address.'
		}
	});
}