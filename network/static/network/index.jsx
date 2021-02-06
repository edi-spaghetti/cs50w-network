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

	constructor(props) {
		super(props)
	}

    render() {
        return (
	        <div className="row">
				<div className="col-2">
					<span>{this.props.user}</span>
				</div>
				<div className="col-8">
					<span>{this.props.content}</span>
				</div>
				<div className="col-2">
					<span>{this.props.timestamp}</span>
				</div>
			</div>
        )
    }
}

class App extends React.Component {

	constructor(props) {
		super(props)

		this.state = {
			posts: [],
			content: ''
		}
	}

	create = (event) => {
		const content = this.state.content
		const t = document.querySelector('input[name = "csrfmiddlewaretoken"]')

		fetch('/api/v1/create', {
			method: 'POST',
			headers: {
				'X-CSRFTOKEN': t.value
			},
			body: JSON.stringify({
				content: content,
				model: 'post'
			})
		})
		.then(response => response.json())
		.then(data => this.insertNewPost(data))

		event.preventDefault()
	}

	insertNewPost = (new_post) => {

		// append post
		this.setState({
			posts: [...this.state.posts, new_post]
		})

		// clear the new post form
		document.querySelector('#new-post-content > textarea').value = ''
		// clear cached state value
		this.setState({
			content: ''
		})
	}

	updateContent = (event) => {
		this.setState({
			content: event.target.value
		})
	}

	componentDidMount() {
		fetch('/api/v1/search?model=post')
		.then(response => response.json())
		.then(posts => this.setState({ posts: posts }))
	}

    render(posts) {
		let data = this.state.posts.map(
			post => <Post
				key={post.id}
				user={post.user}
				timestamp={post.timestamp}
				content={post.content}
			/>
		)

        return (
			// return all posts in order, with new post form inserted at start
			[<NewPost key={0} updateContent={this.updateContent} create={this.create}/>].concat(data)
        )
    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
