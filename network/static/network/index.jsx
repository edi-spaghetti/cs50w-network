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
			posts: []
		}
	}

	componentDidMount() {
		fetch('/api/v1/search?model=post')
		.then(response => response.json())
		.then(posts => this.setState({ posts: posts }))
	}

    render(posts) {
        return (
			this.state.posts.map(post => <Post
				key={post.id}
				user={post.user}
				timestamp={post.timestamp}
				content={post.content}
			/>)
        )
    }
}

ReactDOM.render(<App />, document.querySelector('#network-feed'))
