// TODO: setup bundler
//import cookie from "react-cookies"

class NewPost extends React.Component {

	render() {
		return (
			<div id="new-post-form" className="d-flex flex-column">
				<div id="new-post-title" className="p-2">
					<h4>New Post</h4>
				</div>
				<div id="new-post-content" className="p-2">
				    <textarea placeholder="Your post here" onChange={this.props.updateContent}></textarea>
				</div>
				<div id="new-post-button" className="p-2 ml-auto">
				    <button className="btn btn-primary" onClick={this.props.create}>Post</button>
				</div>
			</div>
		)
	}
}

class Post extends React.Component {

    render() {
        return (
	        <div className="row">
				<div className="col-2">
					<span className="post-item-username" onClick={(event) => this.props.viewProfile(event, this.props.username)}>{this.props.username}</span>
				</div>
				<div className="col-6">
					<span>{this.props.content}</span>
				</div>
				<div className="col-2">
					<span className="icon_heart like-post-button">
						<div className="post-like-count">
							{this.props.like_count}
						</div>
					</span>
				</div>
				<div className="col-2">
					<span>{this.props.timestamp}</span>
				</div>
			</div>
        )
    }
}

class PostFooter extends React.Component {

	render() {

		var previousButton
		if (this.props.hasPrevious) {
			previousButton = React.createElement(
				'button',
				{
					onClick: this.props.loadPrevious,
					className: 'btn btn-secondary'
				},
				'Previous'
			)
		}

		var nextButton
		if (this.props.hasNext) {
			nextButton = React.createElement(
				'button',
				{
					onClick: this.props.loadNext,
					className: 'btn btn-secondary'
				},
				'Next'
			)
		}

		return (
			<div className="row">
				<div className="col-2">
					{previousButton}
				</div>
				<div className="col-8">
					<span>Page {this.props.pageNum} of {this.props.pageCount}</span>
				</div>
				<div className="col-2">
					{nextButton}
				</div>
			</div>
		)
	}

}

class Profile extends React.Component {

	render() {
		// TODO: redesign this widget

		var follow_btn
		if (this.props.data.can_follow) {
			if (this.props.data.is_following) {
				follow_btn = React.createElement(
					'button', {
						onClick: this.props.clickedFollowButton,
						className: 'btn btn-primary'
					}, 'Unfollow'
				)
			}
			else {
				follow_btn = React.createElement(
					'button', {
						onClick: this.props.clickedFollowButton,
						className: 'btn btn-outline-primary'
					}, 'Follow'
				)
			}
		}
		else if (this.props.data.is_self) {
			follow_btn = React.createElement(
					'button', {
						onClick: (event) => {alert('Mmm. Oh Yeah!')},
						className: 'btn btn-outline-danger'
					}, 'This Button Does Nothing... But it feels good!'
				)
		}
		else {
			// if we can't follow and the profile is not the user's own
			// profile we can assume this is an anonymous user
			follow_btn = React.createElement(
				'button', {
					onClick: (event) => {window.location.href = '/login'},
					className: 'btn btn-outline-info'
				}, 'Log in to access more features...'
			)
		}

		return (
	        <div className="d-flex flex-column user-profile">
				<h4>Profile: {this.props.data.username}</h4>
				<h4>Followers: {this.props.data.follower_count}</h4>
				<h4>Following: {this.props.data.leader_count}</h4>
				{follow_btn}
	        </div>
		)
	}
}

class App extends React.Component {

	constructor(props) {
		super(props)

		this.state = {
			user: null,
			page: 'home',
			inData: {},
			outData: {},
			csrfToken: document.querySelector(
				'input[name = "csrfmiddlewaretoken"]').value
		}

		// query server for current user info and update to state
		this.whoami()

		// set navigation bar callbacks
		var mapping = {
			'network-home': this.viewHomePage,
			'my-profile': this.viewMyProfile,
			'all-posts': this.viewAllPosts,
			'my-feed': this.viewFeed
		}
		for (const [key, value] of Object.entries(mapping)) {
			var element = document.querySelector(`#${key}`)
			if (element !== null) {
				element.onclick = value
			}
		}
	}

	// ----------------------------- API METHODS ------------------------------

	/**
	 * Fetches and sets current user data to app state
	 * Avoids having to specify and serialize fields in django template
	 */
	whoami = () => {

		const self = this

		fetch('/api/v1/whoami', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			}
		})
		.then(response => response.json())
		.then((data) => {
			this.setState((state) => {
				state.user = data
				return state
			})
		})

	}

	search = (model, fields, filters, order, limit, newState) => {
		const self = this

		// sanitize params
		if (!model || typeof model != 'string') {
			throw 'Model must be defined'
		}
		fields = fields || null
		filters = filters || null
		order = order || null
		limit = limit || null
		newState = newState || {}

		return fetch('/api/v1/search', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				model: model,
				order: order,
				fields: fields,
				filters: filters,
				limit: limit
			})
		})
		// TODO: error handling on response
		// TODO: caching (and maybe e-tags?) to avoid re-downloading data
		.then(response => response.json())
		.then((data) => {
			this.setState((state) => {
				if (newState.setData || newState.page !== undefined) {
					if (newState.page !== undefined) {
						state.page = newState.page
					}
					if (newState.setData) {
						state.inData[model] = data
					}
				}
				return state
			})
			return data
		})
	}

	update (data, multiOption, onResponse) {

		const self = this

		// TODO: sanitize params

		return fetch('/api/v1/update', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				data: data,
				multiOption: multiOption
			})
		})
		.then(response => response.json())
		.then(onResponse)
	}

	create = (event) => {

		// TODO: generalise this method to be used with other models / data
		// create handle to this for use inside fetch
		const self = this

		fetch('/api/v1/create', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': self.state.csrfToken
			},
			body: JSON.stringify({
				content: self.state.outData.content,
				model: 'post'
			})
		})
		.then(response => response.json())
		.then(data => this.insertNewPost(data))

		event.preventDefault()
	}

	// ----------------------------- STATE METHODS ----------------------------

	insertNewPost = (new_post) => {

		// clear the new post form
		document.querySelector('#new-post-content > textarea').value = ''

		this.setState((state) => {
			// add post to state list
			// TODO: insert by sorted index
			//       currently sorting is hard coded to descending timestamp,
			//       but if I add filters and sorting this will break.
			state.inData.post.data = [new_post, ...state.inData.post.data]
			// clear cached state value
			state.outData.content = ''
			return state
		})
	}

	updateContent = (event) => {
		// setState operate asynchronously, so cache value here
		var newContent = event.target.value
		this.setState((state) => {
			state.outData.content = newContent
			return state
		})
	}

	// --------------------------- EVENT CALLBACKS ----------------------------

	viewHomePage = (event) => {
		// TODO: magical landing page experience
		console.log('clicked home')
		this.setState((state) => {
			state.page = 'home'
			return state
		})
	}

	viewMyProfile = (event) => {
		this.viewProfile(
			event, document.querySelector('#my-profile').dataset.username
		)
	}

	viewAllPosts = (event) => {
		this.search(
			'post', true, null, '-timestamp', null,
			{page: 'posts', setData: true}
		)
	}

	viewFeed = (event) => {

		// first get everyone the current user is following
		var username = document.querySelector('#my-profile').dataset.username
		var filters = [{username: {is: username}}]
		this.search(
			'user', [{leaders: ['id']}], filters, null, 1,
		)
		.then((payload) => {
			var user_ids = payload.data.leaders.map(
				leader => leader.id
			)

			filters = [{user: {in: user_ids}}]
			this.search(
				'post', true, filters, '-timestamp', null,
				{page: 'feed', setData: true}
			)
		})

	}

	viewProfile = (event, username) => {

		var filters = [{username: {is: username}}]
		var fields = [
			'username', 'follower_count', 'leader_count', 'can_follow',
			'is_following', 'is_self', 'id',
			{leaders: ['id']}
		]
		this.search(
			'user', fields, filters, null, 1,
			{setData: true}
		)
		.then((payload) => {
			filters = [{user: {is: payload.data.id}}]
			this.search(
				'post', true, filters, '-timestamp', null,
				{page: 'profile', setData: true}
			)
		})
	}

	clickedFollowButton = (event) => {

		var data = [{
			model: 'user',
			id: this.state.inData.user.data.id,
			followers: this.state.user.id
		}]

		var mode
		if (this.state.inData.user.data.is_following) {
			mode = 'remove'
		}
		else {
			mode = 'add'
		}

		var multiOption = {
			followers: mode
		}

		this.update(data, multiOption, (data) => {
			this.setState((state) => {
				if (mode === 'add') {
					state.inData.user.data.follower_count += 1
					state.inData.user.data.is_following = true
				}
				else {
					state.inData.user.data.follower_count -= 1
					state.inData.user.data.is_following = false
				}
				return state
			})
		})
	}

    render() {

		var pageComponent;
		var footer
		var data = [];  // init as empty array so concat below doesn't fail
		if (this.state.page === 'home') {
			// TODO: pageComponent = <Home />
		}
		else {

			if (this.state.page === 'posts') {
				pageComponent = <NewPost key={0} updateContent={this.updateContent} create={this.create}/>
			}
			else if (this.state.page === 'profile') {
				pageComponent = <Profile key={0} data={this.state.inData.user.data} clickedFollowButton={this.clickedFollowButton}/>
			}
			else if (this.state.page === 'feed') {
				// TODO: pageComponent = <MyFeed />
			}

			// map data to Post components
			data = this.state.inData.post.data.map(
				post => <Post
					key={post.id}
					username={post.username}
					timestamp={post.timestamp}
					content={post.content}
					like_count={post.like_count}
					viewProfile={this.viewProfile}
				/>
			)

			// create footer component from post metadata
			footer = <PostFooter
				key={'post-footer'}
				pageNum={this.state.inData.post.pageNum}
				pageCount={this.state.inData.post.pageCount}
				hasPrevious={this.state.inData.post.hasPrevious}
				hasNext={this.state.inData.post.hasNext}
				loadNext={(event) => {console.log(event)}}
				loadPrevious={(event) => {console.log(event)}}
			/>

		}

		// add list of posts to special component
		return [pageComponent, ...data, footer]

    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
