function AboutYou($form) {
	var self = this;

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